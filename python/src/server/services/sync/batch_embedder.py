"""
Batch embedding with rate limiting for improved API efficiency.

Provides:
- Batch embedding requests (50 texts per call vs 1)
- Rate limiting to prevent API throttling
- Automatic retry on rate limit errors
- Token-aware batching (respects token limits)
"""

import asyncio
from typing import List, Optional
from datetime import datetime, timedelta
from collections import deque
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Token bucket rate limiter for API calls.

    Example:
        limiter = RateLimiter(rate_limit=10, time_window=1.0)

        async with limiter:
            # Make API call
            result = await api.call()
    """

    def __init__(
        self,
        rate_limit: int = 10,
        time_window: float = 1.0
    ):
        """
        Initialize rate limiter.

        Args:
            rate_limit: Maximum requests per time window
            time_window: Time window in seconds
        """
        self.rate_limit = rate_limit
        self.time_window = time_window
        self.request_times: deque = deque()
        self._lock = asyncio.Lock()

    async def __aenter__(self):
        """Enter context manager (acquire rate limit)"""
        await self.acquire()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager"""
        pass

    async def acquire(self):
        """Wait until rate limit allows request"""
        async with self._lock:
            now = datetime.now()

            # Remove old requests outside time window
            cutoff = now - timedelta(seconds=self.time_window)
            while self.request_times and self.request_times[0] < cutoff:
                self.request_times.popleft()

            # Check if at rate limit
            if len(self.request_times) >= self.rate_limit:
                # Calculate wait time
                oldest = self.request_times[0]
                wait_until = oldest + timedelta(seconds=self.time_window)
                wait_seconds = (wait_until - now).total_seconds()

                if wait_seconds > 0:
                    logger.debug(f"Rate limit reached. Waiting {wait_seconds:.2f}s")
                    await asyncio.sleep(wait_seconds)

                # Remove oldest request
                self.request_times.popleft()

            # Record this request
            self.request_times.append(datetime.now())


class BatchEmbedder:
    """
    Batch embedding requests for improved API efficiency.

    Features:
    - Batch multiple texts into single API call (50 texts default)
    - Rate limiting to prevent API throttling
    - Automatic retry on rate limit errors
    - 80%+ reduction in API calls

    Example:
        embedder = BatchEmbedder(
            embedding_service=service,
            batch_size=50,
            rate_limit=10
        )

        texts = ["text1", "text2", ...]
        embeddings = await embedder.embed_batch(texts)
    """

    def __init__(
        self,
        embedding_service,
        batch_size: int = 50,
        rate_limit: int = 10,
        rate_window: float = 1.0,
        max_retries: int = 3
    ):
        """
        Initialize batch embedder.

        Args:
            embedding_service: Service with embed() and embed_batch() methods
            batch_size: Number of texts per batch
            rate_limit: Maximum API requests per time window
            rate_window: Time window for rate limiting (seconds)
            max_retries: Maximum retries on rate limit errors
        """
        self.embedding_service = embedding_service
        self.batch_size = batch_size
        self.rate_limiter = RateLimiter(rate_limit, rate_window)
        self.max_retries = max_retries

    async def embed_batch(self, texts: List[str]) -> List[Optional[List[float]]]:
        """
        Embed texts in batches with rate limiting.

        Args:
            texts: List of text strings to embed

        Returns:
            List of embedding vectors (same order as input)
            None for texts that failed to embed
        """
        if not texts:
            return []

        num_batches = (len(texts) + self.batch_size - 1) // self.batch_size

        logger.info(
            f"Batch embedding: {len(texts)} texts in {num_batches} batches "
            f"(size={self.batch_size})"
        )

        embeddings = []

        # Process in batches
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            batch_num = (i // self.batch_size) + 1

            try:
                # Rate limit and embed batch
                batch_embeddings = await self._embed_batch_with_retry(
                    batch=batch,
                    batch_num=batch_num,
                    total_batches=num_batches
                )

                embeddings.extend(batch_embeddings)

            except Exception as e:
                logger.error(
                    f"Batch {batch_num}/{num_batches} failed after retries: {e}"
                )

                # Fallback: embed individually
                logger.info(f"Falling back to individual embedding for batch {batch_num}")
                individual_embeddings = await self._embed_individually(batch)
                embeddings.extend(individual_embeddings)

        logger.info(
            f"Batch embedding complete: {len(embeddings)}/{len(texts)} successful"
        )

        return embeddings

    async def _embed_batch_with_retry(
        self,
        batch: List[str],
        batch_num: int,
        total_batches: int
    ) -> List[List[float]]:
        """
        Embed batch with retry logic.

        Args:
            batch: List of texts to embed
            batch_num: Current batch number (for logging)
            total_batches: Total number of batches (for logging)

        Returns:
            List of embedding vectors

        Raises:
            Exception if all retries fail
        """
        retries = 0

        while retries <= self.max_retries:
            try:
                # Apply rate limiting
                async with self.rate_limiter:
                    logger.debug(f"Processing batch {batch_num}/{total_batches}")

                    # Check if service has batch method
                    if hasattr(self.embedding_service, 'embed_batch'):
                        return await self.embedding_service.embed_batch(batch)
                    else:
                        # Fallback: call embed() for each text
                        return await self._embed_individually(batch)

            except Exception as e:
                retries += 1

                if retries > self.max_retries:
                    raise

                # Check if rate limit error
                is_rate_limit = self._is_rate_limit_error(e)

                if is_rate_limit:
                    # Exponential backoff for rate limits
                    wait_time = 2 ** retries
                    logger.warning(
                        f"Rate limit hit on batch {batch_num}. "
                        f"Retrying in {wait_time}s (attempt {retries}/{self.max_retries})"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    # Other error - re-raise immediately
                    logger.error(f"Non-rate-limit error on batch {batch_num}: {e}")
                    raise

    async def _embed_individually(self, texts: List[str]) -> List[Optional[List[float]]]:
        """
        Embed texts one at a time (fallback).

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors (None for failures)
        """
        embeddings = []

        for text in texts:
            try:
                async with self.rate_limiter:
                    embedding = await self.embedding_service.embed(text)
                    embeddings.append(embedding)
            except Exception as e:
                logger.error(f"Individual embedding failed: {e}")
                embeddings.append(None)

        return embeddings

    def _is_rate_limit_error(self, error: Exception) -> bool:
        """
        Check if error is due to rate limiting.

        Args:
            error: Exception to check

        Returns:
            True if rate limit error
        """
        error_str = str(error).lower()

        rate_limit_indicators = [
            'rate limit',
            'too many requests',
            'quota exceeded',
            '429',
            'throttle',
            'slow down'
        ]

        return any(indicator in error_str for indicator in rate_limit_indicators)


class TokenAwareBatcher:
    """
    Batch texts while respecting token limits.

    Some embedding APIs have token limits per request.
    This batcher ensures batches don't exceed token limits.

    Example:
        batcher = TokenAwareBatcher(max_tokens_per_batch=8000)

        batches = batcher.create_batches(texts)
        # Each batch respects token limit
    """

    def __init__(
        self,
        max_tokens_per_batch: int = 8000,
        max_items_per_batch: int = 50
    ):
        """
        Initialize token-aware batcher.

        Args:
            max_tokens_per_batch: Maximum tokens per batch
            max_items_per_batch: Maximum items per batch
        """
        self.max_tokens_per_batch = max_tokens_per_batch
        self.max_items_per_batch = max_items_per_batch

    def create_batches(self, texts: List[str]) -> List[List[str]]:
        """
        Create batches that respect token and item limits.

        Args:
            texts: List of texts to batch

        Returns:
            List of batches (each batch is a list of texts)
        """
        batches = []
        current_batch = []
        current_tokens = 0

        for text in texts:
            # Estimate tokens (rough approximation: 4 chars per token)
            estimated_tokens = len(text) // 4

            # Check if adding this text would exceed limits
            would_exceed_tokens = (current_tokens + estimated_tokens) > self.max_tokens_per_batch
            would_exceed_items = len(current_batch) >= self.max_items_per_batch

            if (would_exceed_tokens or would_exceed_items) and current_batch:
                # Start new batch
                batches.append(current_batch)
                current_batch = [text]
                current_tokens = estimated_tokens
            else:
                # Add to current batch
                current_batch.append(text)
                current_tokens += estimated_tokens

        # Add final batch
        if current_batch:
            batches.append(current_batch)

        logger.debug(
            f"Created {len(batches)} batches from {len(texts)} texts "
            f"(avg {len(texts) / len(batches):.1f} per batch)"
        )

        return batches
