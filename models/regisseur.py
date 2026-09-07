from odoo import models, fields


class CommuneRegisseur(models.Model):
    _name = 'commune.regisseur'
    _description = 'Régisseur de recettes'
    _order = 'name'

    name = fields.Char(string='Nom du régisseur', required=True)
    service = fields.Char(string='Service / Fonction')
    matricule = fields.Char(string='Matricule')
    actif = fields.Boolean(string='Actif', default=True)