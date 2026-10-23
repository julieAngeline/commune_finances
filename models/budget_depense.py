from odoo import models, fields, api
from odoo.exceptions import ValidationError


class CommuneBudgetDepense(models.Model):
    _name = 'commune.budget.depense'
    _description = 'Budget de dépense (prévision)'
    _order = 'exercice_id desc, code_compte'

    exercice_id = fields.Many2one(
        'commune.exercice', string="Exercice", required=True, ondelete='restrict')

    code_compte = fields.Char(string="Compte (classe 2 ou 6)", required=True)
    libelle = fields.Char(string="Libellé du compte")

    objet = fields.Char(string="Objet", required=True)

    currency_id = fields.Many2one(
        'res.currency', string="Devise",
        default=lambda self: self.env.company.currency_id, required=True)

    credit_ouvert = fields.Monetary(
        string="Crédit ouvert", currency_field='currency_id', required=True)

    depense_ids = fields.One2many('commune.depense', 'budget_id', string="Dépenses")

    cumule = fields.Monetary(
        string="Cumul", currency_field='currency_id',
        compute='_compute_cumule_disponible', store=True)
    disponible = fields.Monetary(
        string="Disponible", currency_field='currency_id',
        compute='_compute_cumule_disponible', store=True)
    taux_consommation = fields.Float(
        string="Taux de consommation (%)",
        compute='_compute_cumule_disponible', store=True)

    @api.depends('credit_ouvert', 'depense_ids.montant')
    def _compute_cumule_disponible(self):
        for budget in self:
            total = sum(budget.depense_ids.mapped('montant'))
            budget.cumule = total
            budget.disponible = budget.credit_ouvert - total
            budget.taux_consommation = (
                total / budget.credit_ouvert * 100 if budget.credit_ouvert > 0 else 0.0)

    @api.depends('code_compte', 'objet', 'exercice_id.annee')
    def _compute_display_name(self):
        for r in self:
            annee = r.exercice_id.annee or ''
            r.display_name = f"{r.code_compte or ''} - {r.objet or ''} - Exercice {annee}"

    @api.constrains('code_compte')
    def _check_code_compte(self):
        for r in self:
            code = (r.code_compte or '').strip()
            if not code.isdigit() or code[0] not in ('2', '6'):
                raise ValidationError(
                    "Le compte d'une dépense doit être numérique et "
                    "commencer par 2 ou 6 (ex. 6062).")

    @api.constrains('credit_ouvert')
    def _check_credit_ouvert(self):
        for r in self:
            if r.credit_ouvert < 0:
                raise ValidationError("Le crédit ouvert ne peut pas être négatif.")

    _sql_constraints = [
        ('exercice_compte_unique', 'UNIQUE(exercice_id, code_compte)',
         "Un budget existe déjà pour ce compte sur cet exercice.")
    ]