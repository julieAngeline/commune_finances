from odoo import models, fields, api


class CommuneCompteDepense(models.Model):
    _name = 'commune.compte.depense'
    _description = 'Compte comptable de dépense (classe 2 ou 6)'
    _order = 'code_compte'

    code_compte = fields.Char(string='Code compte', required=True)
    libelle = fields.Char(string='Libellé', required=True)

    # ==========================================================
    # NOM D'AFFICHAGE (ODOO 17)
    # ==========================================================

    @api.depends('code_compte', 'libelle')
    def _compute_display_name(self):
        for record in self:
            if record.code_compte and record.libelle:
                record.display_name = f"{record.code_compte} - {record.libelle}"
            else:
                record.display_name = record.code_compte or record.libelle or ''

    # ==========================================================
    # RECHERCHE PAR CODE OU LIBELLÉ DANS LES DROPDOWNS
    # ==========================================================

    @api.model
    def _name_search(self, name='', domain=None, operator='ilike',
                     limit=None, order=None):
        domain = list(domain or [])
        if name:
            domain = ['|',
                      ('code_compte', operator, name),
                      ('libelle', operator, name)] + domain
        return self._search(domain, limit=limit, order=order)