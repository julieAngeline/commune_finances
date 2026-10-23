import datetime
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class CommuneRecette(models.Model):
    _name = 'commune.recette'
    _description = 'Recette Communale'
    _order = 'date_ordre_recette desc, id desc'

    date_versement = fields.Date(string="Date de versement", required=True)

    numero_declaration_recette = fields.Char(string="N° Déclaration de recette")
    date_declaration_recette = fields.Date(string="Date de déclaration de recette")

    numero_ordre_recette = fields.Char(string="N° Ordre de recette", required=True)
    date_ordre_recette = fields.Date(string="Date de l'ordre de recette", required=True)

    periode_debut = fields.Date(string="Période - Début")
    periode_fin = fields.Date(string="Période - Fin")

    montant = fields.Monetary(string="Montant", currency_field='currency_id', required=True)
    currency_id = fields.Many2one(
        'res.currency', string="Devise",
        default=lambda self: self.env.company.currency_id, required=True)

    exercice_id = fields.Many2one(
        'commune.exercice', string="Exercice", required=True, ondelete='restrict')

    # Prévision (compte classe 7). Optionnel pour ne pas casser les données existantes.
    budget_recette_id = fields.Many2one(
        'commune.budget.recette', string="Prévision de recette",
        ondelete='restrict', domain="[('exercice_id', '=', exercice_id)]")
    code_compte = fields.Char(
        string="Compte", related='budget_recette_id.code_compte',
        store=True, readonly=True)

    _sql_constraints = [
        ('numero_ordre_recette_unique', 'UNIQUE(numero_ordre_recette)',
         "Ce numéro d'ordre de recette existe déjà ! Vérifiez avant de continuer.")
    ]

    @api.constrains('montant')
    def _check_montant_positif(self):
        for r in self:
            if r.montant <= 0:
                raise ValidationError("Le montant de la recette doit être supérieur à zéro.")

    @api.constrains('date_ordre_recette', 'date_versement')
    def _check_ordre_versement(self):
        for r in self:
            if r.date_ordre_recette and r.date_versement and r.date_ordre_recette < r.date_versement:
                raise ValidationError(
                    "Impossible : la date de l'ordre de recette ne peut pas être "
                    "antérieure à la date de versement au Trésor.")

    @api.constrains('periode_debut', 'periode_fin')
    def _check_periode_coherente(self):
        for r in self:
            if r.periode_debut and r.periode_fin and r.periode_fin < r.periode_debut:
                raise ValidationError(
                    "La date de fin de période ne peut pas être antérieure à la date de début.")

    @api.constrains('exercice_id', 'budget_recette_id')
    def _check_exercice_budget(self):
        for r in self:
            if r.budget_recette_id and r.budget_recette_id.exercice_id != r.exercice_id:
                raise ValidationError(
                    "La prévision sélectionnée doit appartenir au même exercice que la recette.")

    @api.constrains('exercice_id', 'date_versement')
    def _check_date_limite_complementaire(self):
        for r in self:
            if r.exercice_id and r.date_versement:
                limite = datetime.date(r.exercice_id.annee + 1, 7, 31)
                if r.date_versement > limite:
                    raise ValidationError(
                        f"Impossible : la période complémentaire de l'exercice "
                        f"{r.exercice_id.annee} pour les recettes se termine le "
                        f"31 juillet {r.exercice_id.annee + 1}.")

    @api.constrains('exercice_id', 'montant')
    def _check_periode_saisie(self):
        for r in self:
            if r.exercice_id:
                r.exercice_id._controle_saisie('recette')

    def write(self, vals):
        for r in self:
            r.exercice_id._controle_saisie('recette')
        return super().write(vals)

    def unlink(self):
        for r in self:
            r.exercice_id._controle_saisie('recette', suppression=True)
        return super().unlink()

    @api.constrains('exercice_id')
    def _check_exercice_non_cloture(self):
        for r in self:
            if r.exercice_id and r.exercice_id.etat == 'cloture':
                raise ValidationError(
                    f"Impossible : l'exercice {r.exercice_id.annee} est clôturé. "
                    f"Aucune recette ne peut plus être ajoutée.")

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for r in records:
            if r.exercice_id:
                r.exercice_id.message_post(
                    body=(f"<b>Nouvelle recette enregistrée</b><br/>"
                          f"N° Ordre : {r.numero_ordre_recette}<br/>"
                          f"Montant : {r.montant} {r.currency_id.symbol or ''}"),
                    partner_ids=self.env.user.partner_id.commercial_partner_id.ids,
                    subtype_xmlid='mail.mt_comment',
                )

        self.env['commune.exercice']._recalculer_tous_excedents()
        return records