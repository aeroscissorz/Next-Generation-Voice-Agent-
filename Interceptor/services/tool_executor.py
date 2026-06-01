"""
Direct Tool Executor (Fast-Path)
=================================
Executes common tool queries directly against Supabase, bypassing the
Gemini agent loop entirely. Used by the Interceptor's fast-path to skip
the first LLM round trip for simple, predictable queries.

Fast-Path Architecture:
  1. User sends a message (e.g., "show my invoices")
  2. Interceptor's intent_detector pattern-matches it to a tool name
  3. ToolExecutor fetches the data directly from Supabase
  4. Data is sent to Backend /chat/fast for a single Gemini formatting call
  5. Total latency: ~0.5-1s (vs 3-8s for the full agent loop)

Supported Fast-Path Tools:
  - get_user_invoices      — Simple invoice lookup
  - check_roaming_status   — Roaming status check
  - get_open_tickets       — Open support tickets
  - check_wallet_amount_settlement — Wallet balance
  - bill_explain           — Compound: invoices + breakdowns + roaming (for "why is my bill high?")
  - outage_check           — Compound: invoices (for area) + outages
  - knowledge_search       — RAG: embedding + vector search + keyword fallback

The executor also handles data prefetching on login/new-session to warm
Supabase query caches for faster subsequent requests.
"""

import logging
import os
from typing import Optional

import httpx
from supabase import Client

logger = logging.getLogger("tool_executor")

# Reusable HTTP client for OpenAI embedding calls (knowledge_search fast-path)
_http_client = httpx.Client(timeout=10.0)
_OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# In-memory embedding cache for knowledge_search fast-path
_embedding_cache: dict[str, list] = {}


class ToolExecutor:
    """
    Execute common tools directly against Supabase.
    
    This bypasses the Backend's agent loop for simple queries where we
    know exactly which data to fetch. The result is sent to Backend /chat/fast
    for formatting by a single Gemini call.
    """

    def __init__(self, supabase: Optional[Client]):
        self._sb = supabase
        # Stores prefetched invoice breakdowns for potential fast-path use
        self._prefetched_breakdowns = {}

    def execute(self, tool_name: str, args: dict) -> dict | list | None:
        """
        Run a tool and return its data.
        
        Returns None if the tool is unknown or Supabase is unavailable,
        signaling the caller to fall back to the full agent loop.
        """
        if not self._sb:
            logger.warning("No Supabase client — cannot execute fast-path tool")
            return None

        try:
            return self._dispatch(tool_name, args)
        except Exception as e:
            logger.error(f"Tool executor error ({tool_name}): {e}")
            return None

    def prefetch_user_data(self, user_id: str) -> None:
        """
        Prefetch all common data for a user to warm Supabase query caches.
        Called as a background task on login/new-session.
        
        Data prefetched:
          - Invoices + breakdowns for each invoice
          - Roaming status
          - Open support tickets
          - Wallet balances per invoice
        """
        if not self._sb:
            return
        try:
            # Invoices
            invoices = (
                self._sb.table("invoices")
                .select("*").eq("user_id", user_id)
                .execute().data or []
            )
            # Breakdowns for each invoice (needed for "why is my bill high?" fast-path)
            for inv in invoices:
                inv_id = str(inv.get("invoice_id", ""))
                if inv_id:
                    try:
                        self._sb.table("invoice_breakdown").select("*").eq("invoice_id", inv_id).execute()
                    except Exception:
                        pass
            # Roaming status
            self._sb.table("roaming").select("*").eq("user_id", user_id).execute()
            # Open support tickets
            self._sb.table("support_tickets").select("*").eq("user_id", user_id).eq("status", "open").execute()
            # Wallet balances per invoice (needed for payment flow)
            for inv in invoices:
                inv_id = str(inv.get("invoice_id", ""))
                if inv_id:
                    try:
                        self._sb.table("wallet_amount").select("*").eq("user_id", user_id).eq("invoice_id", inv_id).execute()
                    except Exception:
                        pass

            logger.info(f"⚡ Prefetched all data for user {user_id}")
        except Exception as e:
            logger.warning(f"Prefetch failed for user {user_id}: {e}")

    def _dispatch(self, tool_name: str, args: dict):
        """
        Route a tool call to the appropriate Supabase query.
        Returns the query result or None for unknown tools.
        """
        uid = args.get("user_id", "")

        # ─── Simple Tools (single table query) ──────────────────────────

        if tool_name == "get_user_invoices":
            # Fetch all invoices + eagerly prefetch breakdowns
            invoices = (
                self._sb.table("invoices")
                .select("*")
                .eq("user_id", uid)
                .execute()
                .data or []
            )
            # Prefetch breakdowns for all invoices so follow-ups are faster
            breakdowns = {}
            for inv in invoices:
                inv_id = str(inv.get("invoice_id", ""))
                if inv_id:
                    try:
                        bd = (
                            self._sb.table("invoice_breakdown")
                            .select("*")
                            .eq("invoice_id", inv_id)
                            .execute()
                            .data or []
                        )
                        breakdowns[inv_id] = bd
                    except Exception:
                        pass
            # Store prefetched data for potential fast-path use
            self._prefetched_breakdowns = breakdowns
            return invoices

        if tool_name == "check_roaming_status":
            return (
                self._sb.table("roaming")
                .select("*")
                .eq("user_id", uid)
                .execute()
                .data or []
            )

        if tool_name == "get_open_tickets":
            return (
                self._sb.table("support_tickets")
                .select("*")
                .eq("user_id", uid)
                .eq("status", "open")
                .execute()
                .data or []
            )

        if tool_name == "check_wallet_amount_settlement":
            return (
                self._sb.table("wallet_amount")
                .select("*")
                .eq("user_id", uid)
                .execute()
                .data or []
            )

        # ─── Compound Tools (multiple table queries) ────────────────────

        if tool_name == "bill_explain":
            # "Why is my bill high?" — needs invoices + breakdowns + roaming
            # Fetches everything in one shot so the LLM can explain the charges
            invoices = (
                self._sb.table("invoices")
                .select("*").eq("user_id", uid)
                .execute().data or []
            )
            breakdowns = {}
            for inv in invoices:
                inv_id = str(inv.get("invoice_id", ""))
                if inv_id:
                    try:
                        bd = (
                            self._sb.table("invoice_breakdown")
                            .select("*").eq("invoice_id", inv_id)
                            .execute().data or []
                        )
                        breakdowns[inv_id] = bd
                    except Exception:
                        pass
            roaming = (
                self._sb.table("roaming")
                .select("*").eq("user_id", uid)
                .execute().data or []
            )
            return {
                "invoices": invoices,
                "invoice_breakdowns": breakdowns,
                "roaming": roaming,
            }

        if tool_name == "outage_check":
            # Outage query — needs invoices (to find user's area) + outage records
            invoices = (
                self._sb.table("invoices")
                .select("*").eq("user_id", uid)
                .execute().data or []
            )
            # Extract area from the most recent invoice
            area = None
            if invoices:
                sorted_inv = sorted(invoices, key=lambda x: x.get("invoice_id", 0), reverse=True)
                area = sorted_inv[0].get("area")

            outages = []
            if area:
                outages = (
                    self._sb.table("outages")
                    .select("*").eq("area", area)
                    .execute().data or []
                )

            return {
                "invoices": invoices,
                "area": area,
                "outages": outages,
            }

        # ─── Knowledge Search (RAG via embeddings) ──────────────────────

        if tool_name == "knowledge_search":
            # Semantic search over company knowledge base
            query = args.get("query", "")
            if not query or not _OPENAI_API_KEY:
                return None

            # Get embedding (with in-memory cache)
            cache_key = query.strip().lower()
            if cache_key in _embedding_cache:
                embedding = _embedding_cache[cache_key]
            else:
                try:
                    resp = _http_client.post(
                        "https://api.openai.com/v1/embeddings",
                        headers={
                            "Authorization": f"Bearer {_OPENAI_API_KEY}",
                            "Content-Type": "application/json",
                        },
                        json={"model": "text-embedding-3-small", "input": query},
                    )
                    resp.raise_for_status()
                    embedding = resp.json()["data"][0]["embedding"]
                    _embedding_cache[cache_key] = embedding
                    if len(_embedding_cache) > 200:
                        del _embedding_cache[next(iter(_embedding_cache))]
                except Exception as e:
                    logger.error(f"Embedding API error: {e}")
                    return None

            # Supabase vector similarity search via pgvector RPC
            try:
                results = (
                    self._sb.rpc(
                        "match_company_knowledge",
                        {"query_embedding": embedding, "match_count": 5},
                    ).execute().data or []
                )

                # Fallback to keyword search if vector search returns nothing
                if not results:
                    keyword = query.lower().replace("policy", "").replace("what is your", "").strip()
                    if keyword:
                        results = (
                            self._sb.table("company_knowledge")
                            .select("content")
                            .ilike("content", f"%{keyword}%")
                            .limit(5)
                            .execute().data or []
                        )
                        logger.info(f"Knowledge keyword fallback: {len(results)} results for '{keyword}'")

                return {"query": query, "results": results}
            except Exception as e:
                logger.error(f"Knowledge search error: {e}")
                return None

        logger.warning(f"Unknown fast-path tool: {tool_name}")
        return None
