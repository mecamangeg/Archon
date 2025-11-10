"""
Cohere Reranking Strategy

Implements result reranking using Cohere's Rerank API to improve search result ordering.
The reranking process re-scores search results based on query-document relevance using
Cohere's neural reranking models.

Uses the rerank-english-v3.0 model by default.
"""

import os
from typing import Any

import httpx

from ...config.logfire_config import get_logger, safe_span

logger = get_logger(__name__)

# Default Cohere reranking model
DEFAULT_COHERE_MODEL = "rerank-english-v3.0"

# Cohere API endpoint
COHERE_RERANK_URL = "https://api.cohere.ai/v1/rerank"


class CohereRerankingStrategy:
    """Strategy class implementing result reranking using Cohere's Rerank API"""

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str = DEFAULT_COHERE_MODEL,
        timeout: int = 30
    ):
        """
        Initialize Cohere reranking strategy.

        Args:
            api_key: Cohere API key. If None, will try to load from environment.
            model_name: Name of the Cohere reranking model to use
            timeout: Request timeout in seconds
        """
        self.api_key = api_key or os.getenv("COHERE_API_KEY")
        self.model_name = model_name
        self.timeout = timeout
        self._client = httpx.AsyncClient(timeout=timeout)

    def is_available(self) -> bool:
        """Check if reranking is available (API key is set)."""
        return bool(self.api_key)

    def build_query_document_pairs(
        self, query: str, results: list[dict[str, Any]], content_key: str = "content"
    ) -> tuple[list[str], list[int]]:
        """
        Build document list for the Cohere Rerank API.

        Args:
            query: The search query
            results: List of search results
            content_key: The key in each result dict containing text content

        Returns:
            Tuple of (document texts, valid indices)
        """
        texts = []
        valid_indices = []

        for i, result in enumerate(results):
            content = result.get(content_key, "")
            if content and isinstance(content, str):
                texts.append(content)
                valid_indices.append(i)
            else:
                logger.warning(f"Result {i} has no valid content for reranking")

        return texts, valid_indices

    def apply_rerank_scores(
        self,
        results: list[dict[str, Any]],
        rerank_results: list[dict[str, Any]],
        valid_indices: list[int],
        top_k: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        Apply Cohere reranking scores to results and sort them.

        Args:
            results: Original search results
            rerank_results: Reranking results from Cohere API
            valid_indices: Indices of results that were scored
            top_k: Optional limit on number of results to return

        Returns:
            Reranked and sorted list of results
        """
        # Create a mapping of original index to rerank score
        index_to_score = {}
        for rerank_item in rerank_results:
            original_idx = valid_indices[rerank_item["index"]]
            index_to_score[original_idx] = rerank_item["relevance_score"]

        # Add rerank scores to results
        for i, result in enumerate(results):
            if i in index_to_score:
                result["rerank_score"] = index_to_score[i]
            else:
                result["rerank_score"] = -1.0

        # Sort results by rerank score (descending - highest relevance first)
        reranked_results = sorted(results, key=lambda x: x.get("rerank_score", -1.0), reverse=True)

        # Apply top_k limit if specified
        if top_k is not None and top_k > 0:
            reranked_results = reranked_results[:top_k]

        return reranked_results

    async def rerank_results(
        self,
        query: str,
        results: list[dict[str, Any]],
        content_key: str = "content",
        top_k: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        Rerank search results using Cohere's Rerank API.

        Args:
            query: The search query used to retrieve results
            results: List of search results to rerank
            content_key: The key in each result dict containing text content for reranking
            top_k: Optional limit on number of results to return after reranking

        Returns:
            Reranked list of results ordered by rerank_score (highest first)
        """
        if not self.api_key or not results:
            logger.debug("Reranking skipped - no API key or no results")
            return results

        with safe_span(
            "cohere_rerank_results", result_count=len(results), model_name=self.model_name
        ) as span:
            try:
                # Build document list
                documents, valid_indices = self.build_query_document_pairs(
                    query, results, content_key
                )

                if not documents:
                    logger.warning("No valid texts found for reranking")
                    return results

                # Prepare Cohere API request
                request_data = {
                    "model": self.model_name,
                    "query": query,
                    "documents": documents,
                    "return_documents": False,
                }

                # Add top_k to request if specified
                if top_k is not None and top_k > 0:
                    request_data["top_n"] = min(top_k, len(documents))

                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                }

                # Make API request
                with safe_span("cohere_api_request"):
                    response = await self._client.post(
                        COHERE_RERANK_URL,
                        json=request_data,
                        headers=headers,
                    )
                    response.raise_for_status()
                    data = response.json()

                # Extract reranking results
                rerank_results = data.get("results", [])

                if not rerank_results:
                    logger.warning("Cohere API returned no results")
                    return results

                # Apply scores and sort results
                reranked_results = self.apply_rerank_scores(
                    results, rerank_results, valid_indices, top_k
                )

                # Extract relevance scores for logging
                scores = [item["relevance_score"] for item in rerank_results]
                span.set_attribute("reranked_count", len(reranked_results))
                if scores:
                    span.set_attribute("score_range", f"{min(scores):.3f}-{max(scores):.3f}")
                    logger.debug(
                        f"Reranked {len(documents)} results with Cohere, score range: {min(scores):.3f}-{max(scores):.3f}"
                    )

                return reranked_results

            except httpx.HTTPStatusError as e:
                logger.error(f"Cohere API error: {e.response.status_code} - {e.response.text}")
                span.set_attribute("error", f"HTTP {e.response.status_code}")
                return results
            except Exception as e:
                logger.error(f"Error during Cohere reranking: {e}")
                span.set_attribute("error", str(e))
                return results

    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()

    def get_model_info(self) -> dict[str, Any]:
        """Get information about the Cohere reranking configuration."""
        return {
            "provider": "cohere",
            "model_name": self.model_name,
            "available": self.is_available(),
            "has_api_key": bool(self.api_key),
        }


class CohereRerankingConfig:
    """Configuration helper for Cohere reranking settings"""

    @staticmethod
    def from_credential_service(credential_service) -> dict[str, Any]:
        """Load Cohere reranking configuration from credential service."""
        try:
            # Check if Cohere reranking is enabled
            use_cohere = credential_service.get_bool_setting("USE_COHERE_RERANKING", False)

            # Get API key from credential service
            api_key = credential_service.get_setting("COHERE_API_KEY")

            # Get model name
            model_name = credential_service.get_setting("COHERE_RERANK_MODEL", DEFAULT_COHERE_MODEL)

            # Get top_k setting
            top_k = int(credential_service.get_setting("RERANKING_TOP_K", "0"))

            return {
                "enabled": use_cohere and bool(api_key),
                "api_key": api_key,
                "model_name": model_name,
                "top_k": top_k if top_k > 0 else None,
            }
        except Exception as e:
            logger.error(f"Error loading Cohere reranking config: {e}")
            return {
                "enabled": False,
                "api_key": None,
                "model_name": DEFAULT_COHERE_MODEL,
                "top_k": None,
            }

    @staticmethod
    def from_env() -> dict[str, Any]:
        """Load Cohere reranking configuration from environment variables."""
        api_key = os.getenv("COHERE_API_KEY")
        use_cohere = os.getenv("USE_COHERE_RERANKING", "false").lower() in ("true", "1", "yes", "on")

        return {
            "enabled": use_cohere and bool(api_key),
            "api_key": api_key,
            "model_name": os.getenv("COHERE_RERANK_MODEL", DEFAULT_COHERE_MODEL),
            "top_k": int(os.getenv("RERANKING_TOP_K", "0")) or None,
        }
