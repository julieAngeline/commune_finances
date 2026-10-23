# -*- coding: utf-8 -*-
import json
import logging

import requests

from odoo import models, api

_logger = logging.getLogger(__name__)

MAX_CONTENT_CHARS = 2000


def _truncate(text, limit=MAX_CONTENT_CHARS):
    if not isinstance(text, str):
        text = json.dumps(text, ensure_ascii=False, default=str)
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n... [{len(text) - limit} caractères tronqués]"


def _compact(record):
    out = {}
    for key, value in record.items():
        if key in ("create_uid", "create_date", "write_uid", "write_date",
                   "__last_update", "currency_id", "display_name"):
            continue
        if isinstance(value, list) and len(value) == 2:
            value = value[1] if isinstance(value[1], str) else value[0]
        if value is False or value == [] or value == {}:
            continue
        out[key] = value
    return out


def _summarize(result):
    data = result.get("data")
    payload = data if data is not None else result.get("text", "")
    if isinstance(payload, dict) and "result" in payload and len(payload) <= 2:
        payload = payload["result"]
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except (TypeError, ValueError):
            return _truncate(payload)
    if isinstance(payload, dict):
        payload = _compact(payload)
    elif isinstance(payload, list):
        payload = [_compact(i) if isinstance(i, dict) else i for i in payload[:100]]
    return _truncate(json.dumps(payload, ensure_ascii=False, default=str))


class ChatAgent(models.AbstractModel):
    _name = 'chat.agent'
    _description = 'Agent Ollama (appel LLM synchrone)'

    @api.model
    def _call_ollama(self, messages, tools=None):
        cfg = self.env['chat.config']
        payload = {
            "model": cfg.ollama_model(),
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": 0.1,
                "num_ctx": cfg.ollama_num_ctx(),
            },
        }
        if tools:
            payload["tools"] = tools

        resp = requests.post(
            f"{cfg.ollama_url()}/api/chat",
            json=payload,
            timeout=cfg.ollama_timeout(),
        )
        resp.raise_for_status()
        return resp.json()

    def _extract_tool_calls(self, response):
        message = response.get("message", {})
        calls = []
        for raw in message.get("tool_calls") or []:
            function = raw.get("function", {}) or {}
            name = function.get("name")
            args = function.get("arguments") or {}
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except (TypeError, ValueError):
                    args = {"_raw": args}
            if name:
                calls.append({"name": name, "arguments": args})
        return calls

    @api.model
    def _build_odoo_context(self):
        parts = []

        try:
            exercices = self.env['commune.exercice'].search([], limit=20, order='annee desc')
            if exercices:
                parts.append("Exercices budgétaires (Odoo temps réel):")
                for e in exercices:
                    parts.append(
                        f"  - {e.annee} (état: {e.etat}): "
                        f"total recettes = {e.total_recettes} Ar, "
                        f"total dépenses = {e.total_depenses} Ar, "
                        f"fonds libre = {e.fonds_libre} Ar, "
                        f"excédent N-1 = {e.excedent_n_moins_1} Ar"
                    )
        except Exception as exc:
            _logger.warning("Contexte exercices: %s", exc)

        try:
            budgets = self.env['commune.budget.depense'].search([], limit=100)
            if budgets:
                parts.append("\nBudgets de dépense:")
                for b in budgets:
                    parts.append(
                        f"  - {b.objet or '(sans objet)'}: "
                        f"crédit ouvert = {b.credit_ouvert} Ar, "
                        f"cumulé = {b.cumule} Ar, "
                        f"disponible = {b.disponible} Ar"
                    )
        except Exception as exc:
            _logger.warning("Contexte budgets: %s", exc)

        try:
            nb_rec = self.env['commune.recette'].search_count([])
            nb_dep = self.env['commune.depense'].search_count([])
            parts.append(f"\nNombre de recettes enregistrées: {nb_rec}")
            parts.append(f"Nombre de dépenses enregistrées: {nb_dep}")
        except Exception as exc:
            _logger.warning("Contexte compteurs: %s", exc)

        return "\n".join(parts)

    @api.model
    def run_chat(self, question, history=None, use_tools=False, use_documents=True):
        cfg = self.env['chat.config']
        events = []
        tools_trace = []
        documents = []

        try:
            system_prompt = cfg.system_prompt()
        except Exception:
            system_prompt = "Tu es un assistant financier de la Commune Urbaine de Fianarantsoa. Réponds en français."

        messages = [{"role": "system", "content": system_prompt}]
        for turn in history or []:
            role = turn.get("role")
            content = (turn.get("content") or "").strip()
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": question})

        if use_documents:
            try:
                docs = self.env['chat.rag'].search(question, k=3)
                usable = [d for d in docs if d.get("content") and not d.get("error")]
                if usable:
                    listing = "\n".join(
                        f"[{i}] (source: {d.get('source', 'inconnu')})\n{_truncate(d['content'])}"
                        for i, d in enumerate(usable, 1)
                    )
                    messages.append({
                        "role": "system",
                        "content": "Extraits de documents financiers indexés (RAG) :\n" + listing,
                    })
                    documents = usable
                    events.append({"type": "documents", "count": len(usable)})
            except Exception as exc:
                _logger.warning("RAG context unavailable: %s", exc)
                events.append({"type": "rag_error", "message": str(exc)})

        odoo_context = self._build_odoo_context()
        if odoo_context:
            messages.append({
                "role": "system",
                "content": "Données financières réelles de la CUF (Odoo) :\n" + odoo_context,
            })
            events.append({"type": "odoo_context", "length": len(odoo_context)})

        tools = []
        if use_tools:
            try:
                from .mcp_bridge import bridge
                if not bridge.connected:
                    bridge.connect_sync()
                tools = bridge.ollama_tools()
            except Exception as exc:
                _logger.warning("MCP indisponible: %s", exc)
                events.append({"type": "mcp_error", "message": str(exc)})

        answer_parts = []
        error = None

        for round_index in range(cfg.max_tool_rounds()):
            try:
                response = self._call_ollama(messages, tools=tools or None)
            except Exception as exc:
                error = f"Ollama injoignable ({cfg.ollama_url()}) : {exc}"
                events.append({"type": "error", "message": error})
                break

            message = response.get("message", {})
            content = message.get("content") or ""
            if content:
                answer_parts.append(content)
                events.append({"type": "token", "text": content[:200]})

            tool_calls = self._extract_tool_calls(response)
            if not tool_calls:
                break

            messages.append({
                "role": "assistant",
                "content": content,
                "tool_calls": [
                    {"function": {"name": c["name"], "arguments": json.dumps(c["arguments"])}}
                    for c in tool_calls
                ],
            })

            for call in tool_calls:
                events.append({"type": "tool_call", "name": call["name"],
                               "arguments": call["arguments"], "round": round_index + 1})
                try:
                    from .mcp_bridge import bridge
                    result = bridge.call_json_sync(call["name"], call["arguments"])
                    is_error = result.get("is_error") or (
                        isinstance(result.get("data"), dict) and "error" in result["data"]
                    )
                    summary = _summarize(result)
                except Exception as exc:
                    is_error, summary = True, f"Erreur outil: {exc}"

                tools_trace.append({
                    "name": call["name"], "arguments": call["arguments"],
                    "is_error": is_error, "summary": _truncate(summary, 800),
                })
                events.append({"type": "tool_result", "name": call["name"],
                               "is_error": is_error, "summary": _truncate(summary, 800)})
                messages.append({"role": "tool", "name": call["name"], "content": summary})

        answer = "".join(answer_parts).strip()
        if not answer and not error:
            answer = ("Je n'ai pas obtenu de réponse exploitable. "
                      f"Vérifie que le serveur Ollama ({cfg.ollama_url()}) est démarré "
                      f"et que le modèle '{cfg.ollama_model()}' est disponible.")

        events.append({"type": "done", "answer": answer,
                       "tools": tools_trace, "model": cfg.ollama_model()})

        return {
            "answer": answer,
            "tools": tools_trace,
            "documents": documents,
            "events": events,
            "error": error,
        }