from odoo import models, fields, api
from odoo.exceptions import ValidationError


class CommuneBudgetDepense(models.Model):
    _name = 'commune.budget.depense'
    _description = 'Prévision budgétaire par compte et par exercice'
    _order = 'exercice_id desc, compte_id'

    exercice_id = fields.Many2one('commune.exercice', string='Exercice', required=True)
    compte_id = fields.Many2one('commune.compte.depense', string='Compte', required=True)
    prevision = fields.Monetary(string='Prévision (crédits)', currency_field='currency_id', required=True)
    currency_id = fields.Many2one(
        'res.currency', string='Devise',
        default=lambda self: self.env.company.currency_id
    )

    depense_ids = fields.One2many('commune.depense', 'budget_id', string='Dépenses')

    cumule = fields.Monetary(
        string='Cumul engagé', currency_field='currency_id',
        compute='_compute_cumule', store=True
    )
    disponible = fields.Monetary(
        string='Disponible', currency_field='currency_id',
        compute='_compute_cumule', store=True
    )

    _sql_constraints = [
        ('exercice_compte_unique', 'UNIQUE(exercice_id, compte_id)',
         'Un budget existe déjà pour ce compte sur cet exercice.')
    ]

    @api.depends('prevision', 'depense_ids.montant')
    def _compute_cumule(self):
        for budget in self:
            budget.cumule = sum(budget.depense_ids.mapped('montant'))
            budget.disponible = budget.prevision - budget.cumule

    def name_get(self):
        result = []
        for record in self:
            name = f"{record.compte_id.code_compte} - Exercice {record.exercice_id.annee}"
            result.append((record.id, name))
        return result