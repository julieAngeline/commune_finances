from odoo import models, fields, api
from odoo.exceptions import ValidationError
import datetime

class CommuneExercice(models.Model):
    _name = 'commune.exercice'
    _description = 'Exercice budgétaire'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    annee = fields.Integer(
        string="Année",
        required=True,
        tracking=True
    )

    excedent_n_moins_1 = fields.Monetary(
        string='Excédent exercice N-1',
        currency_field='currency_id',
        help="Excédent reporté de l'année précédente"
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Devise',
        default=lambda self: self.env.company.currency_id
    )

    recette_ids = fields.One2many(
        'commune.recette',
        'exercice_id',
        string='Recettes'
    )

    depense_ids = fields.One2many(
        'commune.depense',
        'exercice_id',
        string='Dépenses'
    )

    total_recettes = fields.Monetary(
        string='Total des recettes',
        currency_field='currency_id',
        compute='_compute_totaux',
        store=True
    )

    total_depenses = fields.Monetary(
        string='Total des dépenses',
        currency_field='currency_id',
        compute='_compute_totaux',
        store=True
    )

    fonds_libre = fields.Monetary(
        string='Fonds Libre',
        currency_field='currency_id',
        compute='_compute_totaux',
        store=True
    )

    @api.depends(
        'excedent_n_moins_1',
        'recette_ids.montant',
        'depense_ids.montant'
    )
    def _compute_totaux(self):
        for record in self:
            record.total_recettes = sum(
                record.recette_ids.mapped('montant')
            )

            record.total_depenses = sum(
                record.depense_ids.mapped('montant')
            )

            record.fonds_libre = (
                record.excedent_n_moins_1
                + record.total_recettes
                - record.total_depenses
            )
    etat = fields.Selection([
        ('ouvert', 'Ouvert'),
        ('complementaire', 'Période complémentaire'),
        ('cloture', 'Clôturé'),
    ], string='État', default='ouvert', required=True)

    def action_passer_periode_complementaire(self):
        for rec in self:
            rec.etat = 'complementaire'

    def action_cloturer(self):
        for rec in self:
            rec.etat = 'cloture'

    def action_reouvrir(self):
        for rec in self:
            rec.etat = 'ouvert'

    @api.constrains('annee')
    def _check_annee_valide(self):
        annee_actuelle = datetime.date.today().year

        for record in self:
            if record.annee > annee_actuelle:
                raise ValidationError(
                    f"Impossible de créer un exercice pour l'année {record.annee}. "
                    f"L'année ne peut pas dépasser l'année en cours ({annee_actuelle})."
                )

            if record.annee < 2000:
                raise ValidationError(
                    "L'année saisie semble incorrecte (trop ancienne)."
                )