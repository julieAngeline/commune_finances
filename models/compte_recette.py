from odoo import models, fields


class CommuneCompteRecette(models.Model):
    _name = 'commune.compte.recette'
    _description = 'Compte comptable de recette (PCOP)'
    _order = 'code_compte'

    code_compte = fields.Char(string='Code compte', required=True)
    libelle = fields.Char(string='Libellé', required=True)

    def name_get(self):
        result = []
        for record in self:
            name = f"{record.code_compte} - {record.libelle}"
            result.append((record.id, name))
        return result