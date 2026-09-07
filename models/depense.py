import re
import datetime

from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo import models, fields, api


class CommuneDepense(models.Model):
    _name = 'commune.depense'
    _description = 'Dépense effectuée'
    _order = 'date_comptable, id'

    numero_bordereau = fields.Char(
        string='N° Bordereau',
        required=True
    )

    exercice_id = fields.Many2one(
        'commune.exercice',
        string='Exercice',
        required=True
    )

    budget_id = fields.Many2one(
        'commune.budget.depense',
        string='Ligne budgétaire',
        required=True,
        domain="[('exercice_id', '=', exercice_id)]"
    )

    compte_id = fields.Many2one(
        related='budget_id.compte_id',
        string='Compte',
        store=True,
        readonly=True
    )

    date_reelle = fields.Date(
        string='Date réelle du paiement',
        required=True
    )

    date_comptable = fields.Date(
        string='Date',
        required=True
    )

    libelle = fields.Char(
        string='Libellé (objet de la dépense)',
        required=True
    )

    beneficiaire = fields.Char(
        string='Bénéficiaire',
        required=True
    )

    montant = fields.Monetary(
        string='Montant',
        currency_field='currency_id',
        required=True
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Devise',
        default=lambda self: self.env.company.currency_id
    )

    prevision = fields.Monetary(
        related='budget_id.prevision',
        string='Prévision',
        currency_field='currency_id',
        store=True,
        readonly=True
    )

    cumule = fields.Monetary(
        string='Cumul',
        currency_field='currency_id',
        compute='_compute_cumule_disponible'
    )

    disponible = fields.Monetary(
        string='Disponible',
        currency_field='currency_id',
        compute='_compute_cumule_disponible'
    )

    _sql_constraints = [
        (
            'numero_bordereau_unique',
            'UNIQUE(numero_bordereau)',
            'Ce numéro de bordereau existe déjà ! Vérifiez avant de continuer.'
        )
    ]

    # ==========================================================
    # CALCUL CUMUL / DISPONIBLE
    # ==========================================================

    @api.depends(
        'montant',
        'date_comptable',
        'budget_id',
        'budget_id.prevision',
        'budget_id.depense_ids.montant',
        'budget_id.depense_ids.date_comptable'
    )
    def _compute_cumule_disponible(self):

        for record in self:

            # Aucun budget
            if not record.budget_id:
                record.cumule = 0
                record.disponible = 0
                continue

            # Prévision du budget
            prevision = record.budget_id.prevision or 0

            # Pas encore de date
            if not record.date_comptable:
                record.cumule = 0
                record.disponible = prevision
                continue

            # Toutes les dépenses de la même ligne budgétaire
            lignes = self.env['commune.depense'].search(
                [
                    ('budget_id', '=', record.budget_id.id),
                    ('date_comptable', '<=', record.date_comptable),
                ],
                order='date_comptable, id'
            )

            cumul = 0

            for ligne in lignes:

                # Si c'est la dépense actuelle déjà enregistrée
                if ligne.id == record.id:
                    cumul += ligne.montant
                    break

                cumul += ligne.montant

            # Si la dépense est nouvelle et n'est pas encore dans la base
            if not record.id:
                cumul += record.montant or 0

            record.cumule = cumul

            # Disponible = Prévision - Cumul
            record.disponible = prevision - cumul

    # ==========================================================
    # DATE COMPTABLE
    # ==========================================================

    @api.onchange('exercice_id', 'date_reelle')
    def _onchange_date_comptable(self):

        if self.exercice_id and self.date_reelle:

            annee = self.exercice_id.annee

            if self.date_reelle.year > annee:
                self.date_comptable = datetime.date(
                    annee,
                    12,
                    31
                )
            else:
                self.date_comptable = self.date_reelle

    # ==========================================================
    # MONTANT POSITIF
    # ==========================================================

    @api.constrains('montant')
    def _check_montant_positif(self):

        for record in self:

            if record.montant <= 0:
                raise ValidationError(
                    "Le montant de la dépense doit être supérieur à zéro."
                )

    # ==========================================================
    # BENEFICIAIRE
    # ==========================================================

    @api.constrains('beneficiaire')
    def _check_beneficiaire_valide(self):

        for record in self:

            if (
                record.beneficiaire
                and re.fullmatch(
                    r'\d+',
                    record.beneficiaire.strip()
                )
            ):
                raise ValidationError(
                    "Le champ Bénéficiaire ne peut pas contenir "
                    "uniquement des chiffres."
                )

    # ==========================================================
    # DEPASSEMENT DU BUDGET
    # ==========================================================

    @api.constrains('montant', 'budget_id')
    def _check_depassement_budget(self):

        for record in self:

            if record.budget_id:

                deja_engage = sum(
                    record.budget_id.depense_ids
                    .filtered(lambda d: d.id != record.id)
                    .mapped('montant')
                )

                if (
                    deja_engage + record.montant
                    > record.budget_id.prevision
                ):
                    raise ValidationError(
                        f"Dépassement de budget ! "
                        f"Prévision : {record.budget_id.prevision}, "
                        f"déjà engagé : {deja_engage}, "
                        f"disponible : "
                        f"{record.budget_id.prevision - deja_engage}."
                    )

    # ==========================================================
    # PERIODE COMPLEMENTAIRE
    # ==========================================================

    @api.constrains('exercice_id', 'date_reelle')
    def _check_date_limite_complementaire(self):

        for record in self:

            if record.exercice_id and record.date_reelle:

                limite = datetime.date(
                    record.exercice_id.annee + 1,
                    1,
                    20
                )

                if record.date_reelle > limite:

                    raise ValidationError(
                        f"Impossible : la période complémentaire "
                        f"de l'exercice {record.exercice_id.annee} "
                        f"pour les dépenses se termine "
                        f"le 20 janvier "
                        f"{record.exercice_id.annee + 1}."
                    )

    # ==========================================================
    # EXERCICE CLOTURE
    # ==========================================================

    @api.constrains('exercice_id')
    def _check_exercice_non_cloture(self):

        for record in self:

            if record.exercice_id.etat == 'cloture':

                raise ValidationError(
                    f"Impossible : l'exercice "
                    f"{record.exercice_id.annee} est clôturé. "
                    f"Aucune dépense ne peut plus y être ajoutée."
                )

    @api.model_create_multi
    def create(self, vals_list):
      records = super().create(vals_list)
      for record in records:
           record.exercice_id.message_post(
            body=f"Nouvelle dépense saisie par {self.env.user.name} : "
                 f"bordereau {record.numero_bordereau}, "
                 f"montant {record.montant} Ar (Bénéficiaire : {record.beneficiaire})."
          )
      return records