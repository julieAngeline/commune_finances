# -*- coding: utf-8 -*-
import json
import logging

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class ChatbotConversation(models.Model):
    _name = 'chatbot.conversation'
    _description = "Conversation avec l'assistant financier"
    _order = 'create_date desc'
    _rec_name = 'titre'

    titre = fields.Char(string="Titre", required=True, default="Nouvelle conversation")
    user_id = fields.Many2one('res.users', string="Utilisateur",
                              default=lambda self: self.env.user,
                              required=True, index=True, ondelete='cascade')
    chat_message_ids = fields.One2many('chatbot.message', 'conversation_id', string="Messages")
    message_count = fields.Integer(string="Nombre de messages",
                                   compute='_compute_message_count', store=True)
    active = fields.Boolean(string="Actif", default=True)
    state = fields.Selection(
        [('brouillon', 'Brouillon'), ('en_cours', 'En cours'), ('archivee', 'Archivée')],
        string="État", default='brouillon')

    @api.depends('chat_message_ids')
    def _compute_message_count(self):
        for conv in self:
            conv.message_count = len(conv.chat_message_ids)

    @api.model
    def create_conversation(self, titre=None):
        conv = self.create({'titre': (titre or 'Nouvelle conversation')[:60]})
        return conv.id

    def envoyer_message(self, question, use_tools=False, use_documents=True):
        self.ensure_one()
        question = (question or "").strip()
        if not question:
            return {
                'answer': "Le message ne peut pas être vide.",
                'sources': [],
                'is_error': True,
                'conversation_id': self.id,
            }

        Message = self.env['chatbot.message']

        previous = Message.search(
            [('conversation_id', '=', self.id)], order='create_date asc, id asc')
        history = [
            {'role': m.role, 'content': m.content}
            for m in previous
            if m.role in ('user', 'assistant') and m.content and not m.is_error
        ]

        Message.create({
            'conversation_id': self.id,
            'role': 'user',
            'content': question,
        })

        try:
            result = self.env['chat.agent'].run_chat(
                question, history=history,
                use_tools=use_tools, use_documents=use_documents,
            )
        except Exception as exc:
            _logger.exception("Chat agent failed")
            result = {
                'answer': f"Erreur de l'assistant : {exc}",
                'error': str(exc),
                'documents': [],
                'tools': [],
                'events': [],
            }

        answer = result.get("answer") or ""
        is_error = bool(result.get("error"))

        Message.create({
            'conversation_id': self.id,
            'role': 'assistant',
            'content': answer or "(aucune réponse)",
            'is_error': is_error,
            'contexte_utilise': bool(result.get("documents")),
            'trace_json': json.dumps(
                {"events": result.get("events", []),
                 "tools": result.get("tools", []),
                 "documents": result.get("documents", [])},
                ensure_ascii=False, default=str),
        })

        if self.state == 'brouillon':
            self.state = 'en_cours'

        sources = [
            {'source': d.get('source'), 'score': d.get('score')}
            for d in (result.get('documents') or [])
        ]

        return {
            'answer': answer or "(aucune réponse)",
            'sources': sources,
            'is_error': is_error,
            'conversation_id': self.id,
        }

    def action_archiver(self):
        self.write({'state': 'archivee', 'active': False})

    def action_reouvrir(self):
        self.write({'state': 'en_cours', 'active': True})


class ChatbotMessage(models.Model):
    _name = 'chatbot.message'
    _description = "Message d'une conversation chatbot"
    _order = 'create_date asc, id asc'
    _rec_name = 'content'

    conversation_id = fields.Many2one('chatbot.conversation', string="Conversation",
                                      required=True, ondelete='cascade', index=True)
    role = fields.Selection(
        [('user', 'Utilisateur'), ('assistant', 'Assistant'), ('system', 'Système')],
        string="Rôle", required=True, default='user')
    content = fields.Text(string="Contenu", required=True)
    is_error = fields.Boolean(string="Erreur", default=False)
    contexte_utilise = fields.Boolean(string="Contexte utilisé", default=False)
    trace_json = fields.Text(string="Trace JSON")