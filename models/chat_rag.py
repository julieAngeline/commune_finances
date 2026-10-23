# -*- coding: utf-8 -*-
import logging
import sys
from pathlib import Path

from odoo import models, api

_logger = logging.getLogger(__name__)


class ChatRag(models.AbstractModel):
    _name = 'chat.rag'
    _description = 'Wrapper RAG (ChromaDB) pour le chatbot'

    def _ensure_path(self):
        rag_dir = self.env['chat.config'].rag_dir()
        if rag_dir and rag_dir not in sys.path:
            sys.path.insert(0, rag_dir)

    @api.model
    def search(self, query, k=5):
        if not query or not query.strip():
            return []
        self._ensure_path()
        try:
            from rag_pipeline import search as _search
            return _search(query, k=k)
        except Exception as exc:
            _logger.exception("RAG search failed: %s", exc)
            return [{"error": str(exc), "query": query}]

    @api.model
    def ingest(self, path=None):
        self._ensure_path()
        target = Path(path) if path else Path(self.env['chat.config'].documents_dir())
        try:
            from rag_pipeline import ingest as _ingest
            return _ingest(target)
        except Exception as exc:
            _logger.exception("RAG ingest failed: %s", exc)
            return {"error": str(exc), "path": str(target)}

    @api.model
    def status(self):
        cfg = self.env['chat.config']
        docs_dir = Path(cfg.documents_dir())
        chroma_dir = Path(cfg.chroma_dir())
        info = {
            "documents_dir": str(docs_dir),
            "chroma_dir": str(chroma_dir),
            "files_on_disk": 0,
            "indexed_chunks": 0,
            "available": False,
        }
        if docs_dir.exists():
            docs = [
                p for p in docs_dir.rglob("*")
                if p.is_file() and p.suffix.lower() in {".pdf", ".docx", ".txt", ".xlsx", ".xls"}
            ]
            info["files_on_disk"] = len(docs)
            info["files"] = [str(p) for p in docs[:50]]
        if chroma_dir.exists():
            try:
                import chromadb
                client = chromadb.PersistentClient(path=str(chroma_dir))
                collection = client.get_collection(cfg.rag_collection())
                info["indexed_chunks"] = collection.count()
                info["available"] = info["indexed_chunks"] > 0
            except Exception as exc:
                info["error"] = str(exc)
        return info