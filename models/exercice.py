from odoo import models, fields, api
from odoo.exceptions import ValidationError


class CommuneExercice(models.Model):
    _name = 'commune.exercice'
    _description = 'Exercice budgétaire'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'annee desc'

    # ==========================================================
    # IDENTIFICATION
    # ==========================================================

    annee = fields.Integer(
        string="Année",
        required=True,
        tracking=True
    )

    excedent_n_moins_1 = fields.Monetary(
        string="Excédent exercice N-1",
        currency_field='currency_id',
        help="Excédent reporté de l'exercice précédent."
    )

    currency_id = fields.Many2one(
        'res.currency',
        string="Devise",
        default=lambda self: self.env.company.currency_id,
        required=True
    )

    # ==========================================================
    # RELATIONS
    # ==========================================================

    recette_ids = fields.One2many(
        'commune.recette',
        'exercice_id',
        string="Recettes"
    )

    budget_ids = fields.One2many(
        'commune.budget.depense',
        'exercice_id',
        string="Budgets de dépenses"
    )

    depense_ids = fields.One2many(
        'commune.depense',
        'exercice_id',
        string="Dépenses"
    )

    # ==========================================================
    # CALCULS FINANCIERS
    # ==========================================================

    total_recettes = fields.Monetary(
        string="Total des recettes",
        currency_field='currency_id',
        compute='_compute_totaux',
        store=True
    )

    total_depenses = fields.Monetary(
        string="Total des dépenses",
        currency_field='currency_id',
        compute='_compute_totaux',
        store=True
    )

    fonds_libre = fields.Monetary(
        string="Fonds libre",
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
        """
        Total recettes = somme des recettes
        Total dépenses = somme des dépenses
        Fonds libre = Excédent N-1 + Total recettes - Total dépenses
        """

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

    # ==========================================================
    # ÉTAT DE L'EXERCICE
    # ==========================================================

    etat = fields.Selection(
        [
            ('ouvert', 'Ouvert'),
            ('complementaire', 'Période complémentaire'),
            ('cloture', 'Clôturé'),
        ],
        string="État",
        default='ouvert',
        required=True,
        tracking=True
    )

    # ==========================================================
    # PASSAGE EN PÉRIODE COMPLÉMENTAIRE
    # ==========================================================

    def action_passer_periode_complementaire(self):
        for record in self:

            if record.etat != 'ouvert':
                raise ValidationError(
                    f"L'exercice {record.annee} doit être ouvert "
                    f"avant de passer en période complémentaire."
                )

            record.etat = 'complementaire'

    # ==========================================================
    # CLÔTURE
    # ==========================================================

    def action_cloturer(self):
        for record in self:

            if record.etat != 'complementaire':
                raise ValidationError(
                    f"L'exercice {record.annee} doit être en "
                    f"période complémentaire avant sa clôture."
                )

            record.etat = 'cloture'

    # ==========================================================
    # RÉOUVERTURE
    # ==========================================================

    def action_reouvrir(self):
        for record in self:

            if record.etat != 'cloture':
                raise ValidationError(
                    f"L'exercice {record.annee} est déjà ouvert "
                    f"ou en période complémentaire."
                )

            record.etat = 'ouvert'

    # ==========================================================
    # CONTRÔLE DE L'ANNÉE
    # ==========================================================

    @api.constrains('annee')
    def _check_annee_valide(self):

        annee_actuelle = fields.Date.today().year

        for record in self:

            if record.annee < 2000:
                raise ValidationError(
                    "L'année saisie semble incorrecte. "
                    "Elle doit être supérieure ou égale à 2000."
                )

            if record.annee > annee_actuelle + 1:
                raise ValidationError(
                    f"Impossible de créer l'exercice {record.annee}. "
                    f"Vous pouvez créer au maximum l'exercice "
                    f"{annee_actuelle + 1}."
                )

    # ==========================================================
    # UNICITÉ DE L'ANNÉE
    # ==========================================================

    _sql_constraints = [
        (
            'annee_unique',
            'UNIQUE(annee)',
            "Un exercice existe déjà pour cette année."
        )
    ]


        # ==========================================================
    # NOM D'AFFICHAGE (ODOO 17)
    # ==========================================================

    @api.depends('annee')
    def _compute_display_name(self):
        for record in self:
            record.display_name = str(record.annee) if record.annee else ''

    # ==========================================================
    # RECHERCHE PAR ANNÉE DANS LES DROPDOWNS
    # ==========================================================

    @api.model
    def _name_search(self, name='', domain=None, operator='ilike',
                     limit=None, order=None):
        domain = list(domain or [])
        if name:
            try:
                domain = [('annee', '=', int(name))] + domain
            except ValueError:
                pass
        return self._search(domain, limit=limit, order=order)