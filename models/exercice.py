import datetime

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class CommuneExercice(models.Model):
    _name = 'commune.exercice'
    _description = 'Exercice budgétaire'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'annee desc'

    annee = fields.Integer(string="Année", required=True, tracking=True)

    currency_id = fields.Many2one(
        'res.currency', string="Devise",
        default=lambda self: self.env.company.currency_id, required=True)

    excedent_n_moins_1 = fields.Monetary(
        string="Excédent exercice N-1", currency_field='currency_id',
        help="Fonds libre de l'exercice précédent (reporté automatiquement).")

    recette_ids = fields.One2many('commune.recette', 'exercice_id', string="Recettes")
    budget_recette_ids = fields.One2many(
        'commune.budget.recette', 'exercice_id', string="Prévisions de recettes")
    budget_ids = fields.One2many(
        'commune.budget.depense', 'exercice_id', string="Budgets de dépenses")
    depense_ids = fields.One2many('commune.depense', 'exercice_id', string="Dépenses")

    total_recettes = fields.Monetary(
        string="Total des recettes", currency_field='currency_id',
        compute='_compute_totaux', store=True)
    total_depenses = fields.Monetary(
        string="Total des dépenses", currency_field='currency_id',
        compute='_compute_totaux', store=True)
    fonds_libre = fields.Monetary(
        string="Fonds libre", currency_field='currency_id',
        compute='_compute_totaux', store=True)

    @api.depends('excedent_n_moins_1', 'recette_ids.montant', 'depense_ids.montant')
    def _compute_totaux(self):
        for record in self:
            record.total_recettes = sum(record.recette_ids.mapped('montant'))
            record.total_depenses = sum(record.depense_ids.mapped('montant'))
            record.fonds_libre = (
                record.excedent_n_moins_1
                + record.total_recettes
                - record.total_depenses
            )

    # ==========================================================
    # ÉTAT : CALCULÉ SELON LA DATE DU JOUR
    # ==========================================================
    etat = fields.Selection(
        [
            ('a_venir', 'À venir'),
            ('ouvert', 'Ouvert'),
            ('complementaire', 'Période complémentaire'),
            ('cloture', 'Clôturé'),
        ],
        string="État", compute='_compute_etat', store=True, readonly=True)

    date_limite_depenses = fields.Date(
        string="Limite dépenses", compute='_compute_dates_limites')
    date_limite_recettes = fields.Date(
        string="Limite recettes Trésor", compute='_compute_dates_limites')

    @staticmethod
    def _etat_pour(annee, today):
        if today < datetime.date(annee, 1, 1):
            return 'a_venir'
        if today <= datetime.date(annee, 12, 31):
            return 'ouvert'
        if today <= datetime.date(annee + 1, 7, 31):
            return 'complementaire'
        return 'cloture'

    @api.depends('annee')
    def _compute_etat(self):
        today = fields.Date.context_today(self)
        for r in self:
            r.etat = self._etat_pour(r.annee, today) if r.annee else 'a_venir'

    @api.depends('annee')
    def _compute_dates_limites(self):
        for r in self:
            if r.annee:
                r.date_limite_depenses = datetime.date(r.annee + 1, 1, 20)
                r.date_limite_recettes = datetime.date(r.annee + 1, 7, 31)
            else:
                r.date_limite_depenses = False
                r.date_limite_recettes = False

    # ==========================================================
    # CONTRÔLE DE SAISIE (appelé par Recette et Dépense)
    # ==========================================================
    def _controle_saisie(self, nature, suppression=False):
        """nature = 'recette' ou 'depense'."""
        today = fields.Date.context_today(self)
        for ex in self:
            etat = self._etat_pour(ex.annee, today)
            if etat == 'a_venir' and not suppression:
                raise ValidationError(
                    f"L'exercice {ex.annee} n'est pas encore ouvert : "
                    f"il commence le 1er janvier {ex.annee}.")
            if etat == 'cloture':
                raise ValidationError(
                    f"L'exercice {ex.annee} est clôturé : aucune opération "
                    f"ne peut être ajoutée, modifiée ou supprimée.")
            if nature == 'depense' and today > datetime.date(ex.annee + 1, 1, 20):
                raise ValidationError(
                    f"Les dépenses de l'exercice {ex.annee} étaient possibles "
                    f"jusqu'au 20 janvier {ex.annee + 1}.")
            if nature == 'recette' and today > datetime.date(ex.annee + 1, 7, 31):
                raise ValidationError(
                    f"Les recettes de l'exercice {ex.annee} étaient possibles "
                    f"jusqu'au 31 juillet {ex.annee + 1}.")

    # ==========================================================
    # EXCÉDENT N-1 AUTOMATIQUE
    # ==========================================================
    def _maj_excedent(self):
        for record in self.sorted('annee'):
            if record.etat == 'cloture':
                continue
            precedent = self.search([('annee', '=', record.annee - 1)], limit=1)
            if precedent:
                record.excedent_n_moins_1 = precedent.fonds_libre

    @api.model
    def _recalculer_tous_excedents(self):
        self.search([], order='annee asc')._maj_excedent()

    # ==========================================================
    # CRON : création automatique + états
    # ==========================================================
    @api.model
    def _cron_maj_etats(self):
        today = fields.Date.context_today(self)
        exos = self.with_context(etat_auto=True)

        # 1. Création automatique : exercice de l'année en cours et de l'année suivante
        existants = exos.search([]).mapped('annee')
        for annee in (today.year, today.year + 1):
            if annee not in existants:
                exos.create({'annee': annee})

        # 2. Mise à jour des états selon la date
        for ex in exos.search([], order='annee asc'):
            nouvel = self._etat_pour(ex.annee, today)
            if ex.etat != nouvel:
                ex.etat = nouvel

        # 3. Report de l'excédent
        self._recalculer_tous_excedents()

    # ==========================================================
    # ACTIONS MANUELLES DÉSACTIVÉES (états automatiques)
    # ==========================================================
    def _refus_manuel(self):
        raise ValidationError(
            "L'état d'un exercice est géré automatiquement selon le calendrier.")

    def action_passer_periode_complementaire(self):
        self._refus_manuel()

    def action_cloturer(self):
        self._refus_manuel()

    def action_reouvrir(self):
        self._refus_manuel()

    def action_recalculer_excedent(self):
        self._recalculer_tous_excedents()

    # ==========================================================
    # EXERCICE CLÔTURÉ = NON MODIFIABLE
    # ==========================================================
    def write(self, vals):
        if not self.env.context.get('etat_auto'):
            for r in self:
                if r.etat == 'cloture':
                    raise ValidationError(
                        f"L'exercice {r.annee} est clôturé : il ne peut plus être modifié.")
        return super().write(vals)

    def unlink(self):
        for r in self:
            if r.etat == 'cloture':
                raise ValidationError(
                    f"L'exercice {r.annee} est clôturé : il ne peut pas être supprimé.")
        return super().unlink()

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        self._recalculer_tous_excedents()
        return records

    # ==========================================================
    # CONTRÔLES
    # ==========================================================
    @api.constrains('annee')
    def _check_annee_valide(self):
        annee_actuelle = fields.Date.today().year
        for record in self:
            if record.annee < 2000:
                raise ValidationError(
                    "L'année saisie semble incorrecte. "
                    "Elle doit être supérieure ou égale à 2000.")
            if record.annee > annee_actuelle + 1:
                raise ValidationError(
                    f"Impossible de créer l'exercice {record.annee}. "
                    f"Vous pouvez créer au maximum l'exercice {annee_actuelle + 1}.")

    _sql_constraints = [
        ('annee_unique', 'UNIQUE(annee)', "Un exercice existe déjà pour cette année.")
    ]

    @api.depends('annee')
    def _compute_display_name(self):
        for record in self:
            record.display_name = str(record.annee) if record.annee else ''