# -*- coding: utf-8 -*-
"""Testy nikdy nevolají API: offline režim zakáže síť v rag.llm() a rag.embed_api() (chybějící cache = chyba, ne volání za peníze)."""
import os

os.environ["RAG_OFFLINE"] = "1"
