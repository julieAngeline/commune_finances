import datetime
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class CommuneRecette(models.Model):
    _name = 'commune.recette'
    _description = 'Recette Communale'
    _order = 'date_ordre_recette desc, id desc'

    # ==========================================================
    # VERSEMENT AU TRÉSOR
    # ==========================================================
    date_versement = fields.Date(
        string="Date de versement",
        required=True
    )

    # ==========================================================
    # DÉCLARATION DE RECETTE
    # ==========================================================
    numero_declaration_recette = fields.Char(
        string="N° Déclaration de recette"
    )
    date_declaration_recette = fields.Date(
        string="Date de déclaration de recette"
    )

    # ==========================================================
    # ORDRE DE RECETTE
    # ==========================================================
    numero_ordre_recette = fields.Char(
        string="N° Ordre de recette",
        required=True
    )
    date_ordre_recette = fields.Date(
        string="Date de l'ordre de recette",
        required=True
    )

    # ==========================================================
    # PÉRIODE
    # ==========================================================
    periode_debut = fields.Date(
        string="Période - Début"
    )
    periode_fin = fields.Date(
        string="Période - Fin"
    )

    # ==========================================================
    # MONTANT
    # ==========================================================
    montant = fields.Monetary(
        string="Montant",
        currency_field='currency_id',
        required=True
    )

    currency_id = fields.Many2one(
        'res.currency',
        string="Devise",
        default=lambda self: self.env.company.currency_id,
        required=True
    )

    # ==========================================================
    # EXERCICE
    # ==========================================================
    exercice_id = fields.Many2one(
        'commune.exercice',
        string="Exercice",
        required=True,
        ondelete='restrict'
    )

    # ==========================================================
    # CONTRAINTE : NUMÉRO D'ORDRE UNIQUE
    # ==========================================================
    _sql_constraints = [
        (
            'numero_ordre_recette_unique',
            'UNIQUE(numero_ordre_recette)',
            "Ce numéro d'ordre de recette existe déjà ! Vérifiez avant de continuer."
        )
    ]

    # ==========================================================
    # CONTRAINTES MÉTIERS
    # ==========================================================
    @api.constrains('montant')
    def _check_montant_positif(self):
        for record in self:
            if record.montant <= 0:
                raise ValidationError("Le montant de la recette doit être supérieur à zéro.")

    @api.constrains('date_ordre_recette', 'date_versement')
    def _check_ordre_versement(self):
        for record in self:
            if record.date_ordre_recette and record.date_versement and record.date_ordre_recette < record.date_versement:
                raise ValidationError(
                    "Impossible : la date de l'ordre de recette ne peut pas être antérieure à la date de versement au Trésor."
                )

    @api.constrains('periode_debut', 'periode_fin')
    def _check_periode_coherente(self):
        for record in self:
            if record.periode_debut and record.periode_fin and record.periode_fin < record.periode_debut:
                raise ValidationError("La date de fin de période ne peut pas être antérieure à la date de début.")

    @api.constrains('exercice_id', 'date_versement')
    def _check_date_limite_complementaire(self):
        for record in self:
            if record.exercice_id and record.date_versement:
                # On suppose que `exercice_id.annee` est un entier (ex: 2025)
                try:
                    annee_exercice = int(record.exercice_id.annee)
                    limite = datetime.date(annee_exercice + 1, 7, 31)
                    if record.date_versement > limite:
                        raise ValidationError(
                            f"Impossible : la période complémentaire de l'exercice {annee_exercice} "
                            f"pour les recettes se termine le 31 juillet {annee_exercice + 1}."
                        )
                except (ValueError, TypeError):
                    pass

    @api.constrains('exercice_id')
    def _check_exercice_non_cloture(self):
        for record in self:
            if record.exercice_id and getattr(record.exercice_id, 'etat', False) == 'cloture':
                raise ValidationError(
                    f"Impossible : l'exercice {record.exercice_id.annee} est clôturé. "
                    f"Aucune recette ne peut plus être ajoutée."
                )

    # ==========================================================
    # NOTIFICATION LORS DE LA CRÉATION
    # ==========================================================
    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            if record.exercice_id:
                record.exercice_id.message_post(
                    body=(
                        f"<b>Nouvelle recette enregistrée</b><br/>"
                        f"N° Ordre : {record.numero_ordre_recette}<br/>"
                        f"Montant : {record.montant} {record.currency_id.symbol or ''}"
                    ),
                    partner_ids=self.env.user.partner_id.commercial_partner_id.ids,
                    subtype_xmlid='mail.mt_comment',
                )
        return records