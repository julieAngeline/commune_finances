import re
from odoo import models, fields, api
from odoo.exceptions import ValidationError
import datetime
from odoo import models, fields, api


class CommuneRecette(models.Model):
    _name = 'commune.recette'
    _description = 'Recette (bordereau du Trésor)'
    _order = 'date_ordre_recette desc'

    # --- Identification (le vrai identifiant unique) ---
    numero_ordre_recette = fields.Char(string="N° Ordre de recette", required=True)
    date_ordre_recette = fields.Date(string="Date de l'ordre de recette", required=True)

    # --- Déclaration (peut se répéter, pas unique) ---
    numero_declaration_recette = fields.Char(string="N° Déclaration de recette")
    date_declaration_recette = fields.Date(string="Date de déclaration de recette")

    # --- Versement au Trésor ---
    date_versement = fields.Date(string="Date de versement au Trésor", required=True)

    # --- Période de versement (début, fin, montant) ---
    periode_debut = fields.Date(string="Période - Début")
    periode_fin = fields.Date(string="Période - Fin")
    periode_montant = fields.Monetary(string="Montant de la période", currency_field='currency_id')

    # --- Rattachements ---
    exercice_id = fields.Many2one('commune.exercice', string='Exercice', required=True)
    compte_id = fields.Many2one('commune.compte.recette', string='Compte', required=True)
    regisseur_id = fields.Many2one('commune.regisseur', string='Régisseur', required=True)

    categorie = fields.Selection([
        ('regie', 'Régie'),
        ('impot', 'Impôt'),
        ('etat_civil', 'État Civil'),
        ('autre', 'Autre'),
    ], string='Catégorie / Service', required=True)

    etat = fields.Selection([
        ('brouillon', 'Brouillon'),
        ('verse_tresor', 'Versé au Trésor'),
        ('valide_tresor', 'Validé par le Trésor'),
        ('ecart', 'Écart détecté'),
    ], string='État', default='brouillon', required=True)

    montant = fields.Monetary(string='Montant', currency_field='currency_id', required=True)
    currency_id = fields.Many2one(
        'res.currency', string='Devise',
        default=lambda self: self.env.company.currency_id
    )
    libelle = fields.Char(string='Libellé / Observation')

    # --- Anti-doublon : sur le vrai identifiant unique ---
    _sql_constraints = [
        ('numero_ordre_recette_unique', 'UNIQUE(numero_ordre_recette)',
         "Ce numéro d'ordre de recette existe déjà ! Vérifiez avant de continuer.")
    ]

    @api.constrains('montant')
    def _check_montant_positif(self):
        for record in self:
            if record.montant <= 0:
                raise ValidationError("Le montant de la recette doit être supérieur à zéro.")

    @api.constrains('date_ordre_recette', 'date_versement')
    def _check_ordre_versement(self):
        for record in self:
            if record.date_ordre_recette < record.date_versement:
                raise ValidationError(
                    "Impossible : l'ordre de recette ne peut pas être daté avant le versement au Trésor. "
                    "Le régisseur doit d'abord verser au Trésor, puis établir l'ordre de recette."
                )

    @api.constrains('periode_debut', 'periode_fin')
    def _check_periode_coherente(self):
        for record in self:
            if record.periode_debut and record.periode_fin and record.periode_fin < record.periode_debut:
                raise ValidationError(
                    "La date de fin de période ne peut pas être antérieure à la date de début."
                )

    @api.constrains('exercice_id', 'date_versement')
    def _check_date_limite_complementaire(self):
        for record in self:
            if record.exercice_id and record.date_versement:
                limite = datetime.date(record.exercice_id.annee + 1, 7, 31)
                if record.date_versement > limite:
                    raise ValidationError(
                        f"Impossible : la période complémentaire de l'exercice "
                        f"{record.exercice_id.annee} pour les recettes se termine "
                        f"le 31 juillet {record.exercice_id.annee + 1}."
                    )

    @api.constrains('exercice_id')
    def _check_exercice_non_cloture(self):
        for record in self:
            if record.exercice_id.etat == 'cloture':
                raise ValidationError(
                    f"Impossible : l'exercice {record.exercice_id.annee} est clôturé. "
                    f"Aucune recette ne peut plus y être ajoutée."
                )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)

        # Utilisateur qui doit recevoir la notification
        responsable = self.env.ref('base.user_admin')

        for record in records:
            record.exercice_id.message_post(
                body=(
                    f"<b>Nouvelle recette saisie</b><br/>"
                    f"Régisseur : {record.regisseur_id.name}<br/>"
                    f"N° ordre de recette : {record.numero_ordre_recette}<br/>"
                    f"Montant : {record.montant} Ar"
                ),
                partner_ids=[responsable.partner_id.id],
                subtype_xmlid='mail.mt_comment',
            )

        return records