from odoo import models, fields, api
from odoo.exceptions import ValidationError


class CommuneBudgetRecette(models.Model):
    _name = 'commune.budget.recette'
    _description = 'Prévision de recette'
    _order = 'exercice_id desc, code_compte'

    exercice_id = fields.Many2one(
        'commune.exercice', string="Exercice", required=True, ondelete='restrict')

    code_compte = fields.Char(string="Compte (classe 7)", required=True)
    libelle = fields.Char(string="Libellé du compte")
    objet = fields.Char(string="Objet", required=True)

    currency_id = fields.Many2one(
        'res.currency', string="Devise",
        default=lambda self: self.env.company.currency_id, required=True)

    prevision = fields.Monetary(
        string="Prévision", currency_field='currency_id', required=True)

    recette_ids = fields.One2many(
        'commune.recette', 'budget_recette_id', string="Recettes")

    cumule = fields.Monetary(
        string="Cumul réalisé", currency_field='currency_id',
        compute='_compute_realisation', store=True)
    ecart = fields.Monetary(
        string="Écart (réalisé - prévision)", currency_field='currency_id',
        compute='_compute_realisation', store=True)
    taux_realisation = fields.Float(
        string="Taux de réalisation (%)",
        compute='_compute_realisation', store=True)

    @api.depends('prevision', 'recette_ids.montant')
    def _compute_realisation(self):
        # AUCUNE limite : une recette peut dépasser la prévision.
        for b in self:
            total = sum(b.recette_ids.mapped('montant'))
            b.cumule = total
            b.ecart = total - b.prevision
            b.taux_realisation = (
                total / b.prevision * 100 if b.prevision > 0 else 0.0
            )

    @api.depends('code_compte', 'objet', 'exercice_id.annee')
    def _compute_display_name(self):
        for r in self:
            annee = r.exercice_id.annee or ''
            r.display_name = f"{r.code_compte or ''} - {r.objet or ''} - Exercice {annee}"

    @api.constrains('code_compte')
    def _check_code_compte(self):
        for r in self:
            code = (r.code_compte or '').strip()
            if not code.isdigit() or not code.startswith('7'):
                raise ValidationError(
                    "Le compte d'une recette doit être numérique et "
                    "commencer par 7 (ex. 77211).")

    @api.constrains('prevision')
    def _check_prevision(self):
        for r in self:
            if r.prevision < 0:
                raise ValidationError("La prévision ne peut pas être négative.")

    _sql_constraints = [
        ('exercice_compte_recette_unique', 'UNIQUE(exercice_id, code_compte)',
         "Une prévision existe déjà pour ce compte sur cet exercice.")
    ]