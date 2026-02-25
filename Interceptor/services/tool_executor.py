"""
Direct Tool Executor
Calls backend tools directly via Supabase, bypassing the Gemini agent.
Used by the fast-path to skip the first LLM round trip.
"""

import logging
import os
from typing import Optional

import httpx
from supabase import Client

logger = logging.getLogger("tool_executor")

# Reusable HTTP client for OpenAI embedding calls
_http_client = httpx.Client(timeout=10.0)
_OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
_embedding_cache: dict[str, list] = {}


class ToolExecutor:
    """Execute common tools directly against Supabase."""

    def __init__(self, supabase: Optional[Client]):
        self._sb = supabase
        self._prefetched_breakdowns = {}

    def execute(self, tool_name: str, args: dict) -> dict | list | None:
        """Run a tool and return its data. Returns None if tool unknown or Supabase unavailable."""
        if not self._sb:
            logger.warning("No Supabase client — cannot execute fast-path tool")
            return None

        try:
            return self._dispatch(tool_name, args)
        except Exception as e:
            logger.error(f"Tool executor error ({tool_name}): {e}")
            return None

    def prefetch_user_data(self, user_id: str) -> None:
        """Prefetch all common data for a user to warm caches."""
        if not self._sb:
            return
        try:
            # Invoices
            invoices = (
                self._sb.table("invoices")
                .select("*").eq("user_id", user_id)
                .execute().data or []
            )
            # Breakdowns for each invoice
            for inv in invoices:
                inv_id = str(inv.get("invoice_id", ""))
                if inv_id:
                    try:
                        self._sb.table("invoice_breakdown").select("*").eq("invoice_id", inv_id).execute()
                    except Exception:
                        pass
            # Roaming
            self._sb.table("roaming").select("*").eq("user_id", user_id).execute()
            # Tickets
            self._sb.table("support_tickets").select("*").eq("user_id", user_id).eq("status", "open").execute()
            # Wallet
            self._sb.table("wallet_amount").select("*").eq("user_id", user_id).execute()
            # Payment methods
            try:
                self._sb.table("payment_methods").select("methods").eq("user_id", user_id).single().execute()
            except Exception:
                pass

            logger.info(f"⚡ Prefetched all data for user {user_id}")
        except Exception as e:
            logger.warning(f"Prefetch failed for user {user_id}: {e}")

    def _dispatch(self, tool_name: str, args: dict):
        uid = args.get("user_id", "")

        if tool_name == "get_user_invoices":
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

        if tool_name == "get_payment_methods":
            res = (
                self._sb.table("payment_methods")
                .select("methods")
                .eq("user_id", uid)
                .single()
                .execute()
            )
            return res.data.get("methods", []) if res.data else []

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

        if tool_name == "bill_explain":
            # Fetch invoices + all breakdowns in one shot
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
            # Fetch invoices to find user's area, then check outages
            invoices = (
                self._sb.table("invoices")
                .select("*").eq("user_id", uid)
                .execute().data or []
            )
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

        if tool_name == "knowledge_search":
            # Vector search against company_knowledge table
            query = args.get("query", "")
            if not query or not _OPENAI_API_KEY:
                return None

            # Get embedding (with cache)
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

            # Supabase vector search
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
