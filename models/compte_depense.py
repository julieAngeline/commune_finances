from odoo import models, fields


class CommuneCompteDepense(models.Model):
    _name = 'commune.compte.depense'
    _description = 'Compte comptable de dépense (classe 2 ou 6)'
    _order = 'code_compte'

    code_compte = fields.Char(string='Code compte', required=True)
    libelle = fields.Char(string='Libellé', required=True)

    def name_get(self):
        result = []
        for record in self:
            result.append((record.id, f"{record.code_compte} - {record.libelle}"))
        return result