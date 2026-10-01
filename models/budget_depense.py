from odoo import models, fields, api
from odoo.exceptions import ValidationError


class CommuneBudgetDepense(models.Model):
    _name = 'commune.budget.depense'
    _description = 'Budget de dépense'
    _order = 'exercice_id desc, compte_id'

    # ==========================================================
    # EXERCICE ET COMPTE
    # ==========================================================

    exercice_id = fields.Many2one(
        'commune.exercice',
        string="Exercice",
        required=True,
        ondelete='restrict'
    )

    compte_id = fields.Many2one(
        'commune.compte.depense',
        string="Compte",
        required=True,
        ondelete='restrict'
    )

    # ==========================================================
    # INFORMATIONS ET MONTANTS
    # ==========================================================

    objet = fields.Char(
        string="Objet",
        required=True
    )

    currency_id = fields.Many2one(
        'res.currency',
        string="Devise",
        default=lambda self: self.env.company.currency_id,
        required=True
    )

    credit_ouvert = fields.Monetary(
        string="Crédit ouvert",
        currency_field='currency_id',
        required=True
    )

    depense_ids = fields.One2many(
        'commune.depense',
        'budget_id',
        string="Dépenses"
    )

    # ==========================================================
    # CHAMPS CALCULÉS
    # ==========================================================

    cumule = fields.Monetary(
        string="Cumul",
        currency_field='currency_id',
        compute='_compute_cumule_disponible',
        store=True
    )

    disponible = fields.Monetary(
        string="Disponible",
        currency_field='currency_id',
        compute='_compute_cumule_disponible',
        store=True
    )

    taux_consommation = fields.Float(
        string="Taux de consommation (%)",
        compute='_compute_cumule_disponible',
        store=True
    )

    @api.depends('credit_ouvert', 'depense_ids.montant')
    def _compute_cumule_disponible(self):
        for budget in self:
            total_cumule = sum(budget.depense_ids.mapped('montant'))
            disponible = budget.credit_ouvert - total_cumule
            
            # Calcul du taux
            if budget.credit_ouvert > 0:
                taux = (total_cumule / budget.credit_ouvert) * 100
            else:
                taux = 0.0

            budget.cumule = total_cumule
            budget.disponible = disponible
            budget.taux_consommation = taux

    # ==========================================================
    # NOM D'AFFICHAGE (ODOO 17+)
    # ==========================================================

    @api.depends('compte_id.code_compte', 'objet', 'exercice_id.annee')
    def _compute_display_name(self):
        for record in self:
            code = record.compte_id.code_compte if record.compte_id else ''
            annee = record.exercice_id.annee if record.exercice_id else ''
            record.display_name = f"{code} - {record.objet} - Exercice {annee}".strip(" -")

    # ==========================================================
    # CONTRÔLES ET CONTRAINTES
    # ==========================================================

    @api.constrains('credit_ouvert')
    def _check_credit_ouvert(self):
        for record in self:
            if record.credit_ouvert < 0:
                raise ValidationError("Le crédit ouvert ne peut pas être négatif.")

    _sql_constraints = [
        (
            'exercice_compte_unique',
            'UNIQUE(exercice_id, compte_id)',
            "Un budget existe déjà pour ce compte sur cet exercice."
        )
    ]