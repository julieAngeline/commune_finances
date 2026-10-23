import datetime
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class CommuneDepense(models.Model):
    _name = 'commune.depense'
    _description = 'Dépense effectuée'
    _order = 'date desc, id desc'

    exercice_id = fields.Many2one(
        'commune.exercice', string="Exercice", required=True, ondelete='restrict')

    budget_id = fields.Many2one(
        'commune.budget.depense', string="Budget de dépense", required=True,
        ondelete='restrict', domain="[('exercice_id', '=', exercice_id)]")

    # Compte = attribut repris du budget (identifie le compte débité)
    code_compte = fields.Char(
        string="Compte", related='budget_id.code_compte', store=True, readonly=True)
    libelle_compte = fields.Char(
        string="Libellé compte", related='budget_id.libelle', readonly=True)

    date = fields.Date(string="Date", required=True)
    objet = fields.Char(string="Objet", required=True)

    currency_id = fields.Many2one(
        'res.currency', string="Devise",
        default=lambda self: self.env.company.currency_id, required=True)

    credit_ouvert = fields.Monetary(
        string="Crédit ouvert", related='budget_id.credit_ouvert',
        currency_field='currency_id', store=True, readonly=True)

    montant = fields.Monetary(string="Montant", currency_field='currency_id', required=True)

    cumule = fields.Monetary(
        string="Cumul", currency_field='currency_id', compute='_compute_cumule_disponible')
    disponible = fields.Monetary(
        string="Disponible", currency_field='currency_id', compute='_compute_cumule_disponible')

    @api.depends('budget_id', 'budget_id.credit_ouvert', 'budget_id.depense_ids.montant', 'montant')
    def _compute_cumule_disponible(self):
        for r in self:
            if not r.budget_id:
                r.cumule = 0
                r.disponible = 0
                continue
            autres = r.budget_id.depense_ids.filtered(lambda d: d.id != r.id)
            cumul = sum(autres.mapped('montant')) + (r.montant or 0)
            r.cumule = cumul
            r.disponible = r.budget_id.credit_ouvert - cumul

    @api.constrains('montant')
    def _check_montant_positif(self):
        for r in self:
            if r.montant <= 0:
                raise ValidationError("Le montant de la dépense doit être supérieur à zéro.")

    @api.constrains('exercice_id', 'budget_id')
    def _check_exercice_budget(self):
        for r in self:
            if r.exercice_id and r.budget_id and r.budget_id.exercice_id != r.exercice_id:
                raise ValidationError(
                    "Le budget sélectionné doit appartenir au même exercice que la dépense.")

    @api.constrains('montant', 'budget_id')
    def _check_depassement_budget(self):
        # La dépense, elle, est LIMITÉE par le crédit ouvert.
        for r in self:
            if not r.budget_id:
                continue
            autres = r.budget_id.depense_ids.filtered(lambda d: d.id != r.id)
            deja = sum(autres.mapped('montant'))
            dispo = r.budget_id.credit_ouvert - deja
            if r.montant > dispo:
                raise ValidationError(
                    f"Dépassement du crédit ouvert !\n\n"
                    f"Crédit ouvert : {r.budget_id.credit_ouvert}\n"
                    f"Déjà dépensé : {deja}\n"
                    f"Disponible : {dispo}\n"
                    f"Montant demandé : {r.montant}")

    @api.constrains('exercice_id')
    def _check_exercice_non_cloture(self):
        for r in self:
            if r.exercice_id and r.exercice_id.etat == 'cloture':
                raise ValidationError(
                    f"Impossible : l'exercice {r.exercice_id.annee} est clôturé. "
                    f"Aucune dépense ne peut plus être ajoutée.")

    @api.constrains('exercice_id', 'date')
    def _check_date_limite_complementaire(self):
        for r in self:
            if r.exercice_id and r.date:
                limite = datetime.date(r.exercice_id.annee + 1, 1, 20)
                if r.date > limite:
                    raise ValidationError(
                        f"Impossible : la période complémentaire de l'exercice "
                        f"{r.exercice_id.annee} pour les dépenses se termine le "
                        f"20 janvier {r.exercice_id.annee + 1}.")

    @api.constrains('exercice_id', 'montant')
    def _check_periode_saisie(self):
        for r in self:
            if r.exercice_id:
                r.exercice_id._controle_saisie('depense')

    def write(self, vals):
        for r in self:
            r.exercice_id._controle_saisie('depense')
        return super().write(vals)

    def unlink(self):
        for r in self:
            r.exercice_id._controle_saisie('depense', suppression=True)
        return super().unlink()

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        self.env['commune.exercice']._recalculer_tous_excedents()
        return records