# -*- coding: utf-8 -*-
from odoo import models, api

SYSTEM_PROMPT_DEFAULT = """Tu es un assistant intelligent spécialisé dans le suivi des
ressources financières de la Commune Urbaine de Fianarantsoa.

RÈGLES STRICTES
1. Utilise uniquement les données présentes dans le contexte fourni par Odoo
   ou dans les résultats des outils autorisés.
2. N'invente jamais de montant, d'année, de recette, de dépense, d'excédent,
   de compte ou d'information financière.
3. Ne suppose jamais qu'une donnée manquante vaut zéro.
4. Si une information est absente, réponds :
   "Information indisponible dans les données fournies."
5. Réponds en français, de manière claire, concise et professionnelle.

Fonds libre = Excédent N-1 + Total des recettes - Total des dépenses
"""


class ChatConfig(models.AbstractModel):
    _name = 'chat.config'
    _description = 'Configuration du chatbot IA'

    @api.model
    def _get(self, key, default=None):
        return self.env['ir.config_parameter'].sudo().get_param(
            f'commune_finances.{key}', default)

    @api.model
    def ollama_url(self):
        return self._get('ollama_url', 'http://localhost:11434')

    @api.model
    def ollama_model(self):
        return self._get('ollama_model', 'llama3.2:1b')

    @api.model
    def ollama_timeout(self):
        return int(self._get('ollama_timeout', '300'))

    @api.model
    def ollama_num_ctx(self):
        return int(self._get('ollama_num_ctx', '2048'))

    @api.model
    def max_tool_rounds(self):
        return int(self._get('max_tool_rounds', '3'))

    @api.model
    def chroma_dir(self):
        return self._get(
            'chroma_dir',
            r'C:\Program Files\Odoo 17.0.20260702\server\Custom\commune_finances\chroma_db',
        )

    @api.model
    def documents_dir(self):
        return self._get(
            'documents_dir',
            r'C:\Program Files\Odoo 17.0.20260702\server\Custom\commune_finances\documents',
        )

    @api.model
    def rag_dir(self):
        return self._get('rag_dir', '')
    
    @api.model
    def rag_collection(self):
        return self._get('rag_collection', 'cuf-financial-docs')

    @api.model
    def system_prompt(self):
        return self._get('system_prompt', SYSTEM_PROMPT_DEFAULT)