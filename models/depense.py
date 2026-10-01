from odoo import models, fields, api
from odoo.exceptions import ValidationError
import datetime


class CommuneDepense(models.Model):
    _name = 'commune.depense'
    _description = 'Dépense effectuée'
    _order = 'date desc, id desc'

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
    # LIGNE BUDGÉTAIRE
    # ==========================================================

    budget_id = fields.Many2one(
        'commune.budget.depense',
        string="Budget de dépense",
        required=True,
        ondelete='restrict',
        domain="[('exercice_id', '=', exercice_id)]"
    )

    # ==========================================================
    # COMPTE
    # RÉCUPÉRÉ AUTOMATIQUEMENT DU BUDGET
    # ==========================================================

    compte_id = fields.Many2one(
        'commune.compte.depense',
        string="Compte",
        related='budget_id.compte_id',
        store=True,
        readonly=True
    )

    # ==========================================================
    # DATE
    # ==========================================================

    date = fields.Date(
        string="Date",
        required=True
    )

    # ==========================================================
    # OBJET
    # ==========================================================

    objet = fields.Char(
        string="Objet",
        required=True
    )

    # ==========================================================
    # CRÉDIT OUVERT
    # RÉCUPÉRÉ AUTOMATIQUEMENT DU BUDGET
    # ==========================================================

    credit_ouvert = fields.Monetary(
        string="Crédit ouvert",
        related='budget_id.credit_ouvert',
        currency_field='currency_id',
        store=True,
        readonly=True
    )

    # ==========================================================
    # MONTANT DE LA DÉPENSE
    # ==========================================================

    montant = fields.Monetary(
        string="Montant",
        currency_field='currency_id',
        required=True
    )

    # ==========================================================
    # CUMUL
    # ==========================================================

    cumule = fields.Monetary(
        string="Cumul",
        currency_field='currency_id',
        compute='_compute_cumule_disponible'
    )

    # ==========================================================
    # DISPONIBLE
    # ==========================================================

    disponible = fields.Monetary(
        string="Disponible",
        currency_field='currency_id',
        compute='_compute_cumule_disponible'
    )

    # ==========================================================
    # DEVISE
    # ==========================================================

    currency_id = fields.Many2one(
        'res.currency',
        string="Devise",
        default=lambda self: self.env.company.currency_id,
        required=True
    )

    # ==========================================================
    # CALCUL DU CUMUL ET DU DISPONIBLE
    # ==========================================================

    @api.depends(
        'budget_id',
        'budget_id.credit_ouvert',
        'budget_id.depense_ids.montant',
        'montant'
    )
    def _compute_cumule_disponible(self):

        for record in self:

            if not record.budget_id:

                record.cumule = 0
                record.disponible = 0

                continue

            depenses = record.budget_id.depense_ids

            cumul = sum(
                depenses.filtered(
                    lambda d: d.id != record.id
                ).mapped('montant')
            )

            cumul += record.montant or 0

            record.cumule = cumul

            record.disponible = (
                record.budget_id.credit_ouvert
                - cumul
            )

    # ==========================================================
    # MONTANT POSITIF
    # ==========================================================

    @api.constrains('montant')
    def _check_montant_positif(self):

        for record in self:

            if record.montant <= 0:

                raise ValidationError(
                    "Le montant de la dépense doit être "
                    "supérieur à zéro."
                )

    # ==========================================================
    # EXERCICE ET BUDGET COHÉRENTS
    # ==========================================================

    @api.constrains(
        'exercice_id',
        'budget_id'
    )
    def _check_exercice_budget(self):

        for record in self:

            if (
                record.exercice_id
                and record.budget_id
                and record.budget_id.exercice_id
                != record.exercice_id
            ):
                raise ValidationError(
                    "Le budget sélectionné doit appartenir "
                    "au même exercice que la dépense."
                )

    # ==========================================================
    # DÉPASSEMENT DU CRÉDIT
    # ==========================================================

    @api.constrains(
        'montant',
        'budget_id'
    )
    def _check_depassement_budget(self):

        for record in self:

            if not record.budget_id:
                continue

            autres_depenses = record.budget_id.depense_ids.filtered(
                lambda d: d.id != record.id
            )

            deja_depense = sum(
                autres_depenses.mapped('montant')
            )

            disponible_avant = (
                record.budget_id.credit_ouvert
                - deja_depense
            )

            if record.montant > disponible_avant:

                raise ValidationError(
                    f"Dépassement du crédit ouvert !\n\n"
                    f"Crédit ouvert : "
                    f"{record.budget_id.credit_ouvert}\n"
                    f"Déjà dépensé : "
                    f"{deja_depense}\n"
                    f"Disponible : "
                    f"{disponible_avant}\n"
                    f"Montant demandé : "
                    f"{record.montant}"
                )

    # ==========================================================
    # EXERCICE CLÔTURÉ
    # ==========================================================

    @api.constrains('exercice_id')
    def _check_exercice_non_cloture(self):

        for record in self:

            if (
                record.exercice_id
                and record.exercice_id.etat == 'cloture'
            ):

                raise ValidationError(
                    f"Impossible : l'exercice "
                    f"{record.exercice_id.annee} est clôturé. "
                    f"Aucune dépense ne peut plus être ajoutée."
                )

    # ==========================================================
    # PÉRIODE COMPLÉMENTAIRE (LIMITE 20 JANVIER N+1)
    # ==========================================================

    @api.constrains(
        'exercice_id',
        'date'
    )
    def _check_date_limite_complementaire(self):

        for record in self:

            if (
                record.exercice_id
                and record.date
            ):

                limite = datetime.date(
                    record.exercice_id.annee + 1,
                    1,
                    20
                )

                if record.date > limite:

                    raise ValidationError(
                        f"Impossible : la période complémentaire "
                        f"de l'exercice {record.exercice_id.annee} "
                        f"pour les dépenses se termine le "
                        f"20 janvier {record.exercice_id.annee + 1}."
                    )