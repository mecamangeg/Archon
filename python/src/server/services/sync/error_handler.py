"""
Error handling utilities for sync operations.

Provides:
- Retry logic with exponential backoff
- Circuit breaker pattern for failing projects
- Error classification and user-friendly messages
- Structured error logging
"""

from dataclasses import dataclass
from typing import Callable, Any, Optional, Dict
from enum import Enum
from datetime import datetime, timedelta
import asyncio
import logging
import random
from functools import wraps

logger = logging.getLogger(__name__)


@dataclass
class RetryConfig:
    """Configuration for retry behavior"""
    max_retries: int = 3
    initial_delay: float = 1.0  # seconds
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True


def retry_with_backoff(config: RetryConfig = RetryConfig()):
    """
    Decorator to retry async functions with exponential backoff.

    Usage:
        @retry_with_backoff(RetryConfig(max_retries=5))
        async def fetch_data():
            ...

    Args:
        config: Retry configuration

    Returns:
        Decorated function with retry logic
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            retries = 0
            delay = config.initial_delay

            while retries <= config.max_retries:
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    retries += 1

                    # Don't retry on final attempt
                    if retries > config.max_retries:
                        logger.error(
                            f"Function {func.__name__} failed after {retries} retries: {e}",
                            exc_info=True
                        )
                        raise

                    # Calculate backoff delay
                    if config.jitter:
                        jitter_factor = random.uniform(0.5, 1.5)
                        actual_delay = min(delay * jitter_factor, config.max_delay)
                    else:
                        actual_delay = min(delay, config.max_delay)

                    logger.warning(
                        f"Function {func.__name__} failed (attempt {retries}/{config.max_retries}): {e}. "
                        f"Retrying in {actual_delay:.2f}s..."
                    )

                    await asyncio.sleep(actual_delay)
                    delay *= config.exponential_base

        return wrapper
    return decorator


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Failures detected, blocking requests
    HALF_OPEN = "half_open"  # Testing if system recovered


class CircuitBreaker:
    """
    Circuit breaker to prevent repeated failures.

    States:
    - CLOSED: Normal operation
    - OPEN: Too many failures, block requests for timeout period
    - HALF_OPEN: Allow one test request to check if system recovered

    Example:
        breaker = CircuitBreaker(failure_threshold=5, timeout=60.0)

        try:
            result = await breaker.call(lambda: risky_operation())
        except CircuitBreakerOpenError:
            # Circuit is open, don't attempt operation
            pass
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: float = 60.0,  # seconds
        half_open_max_calls: int = 1
    ):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            timeout: Seconds to wait before transitioning from OPEN to HALF_OPEN
            half_open_max_calls: Max concurrent calls allowed in HALF_OPEN state
        """
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.half_open_max_calls = half_open_max_calls

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.half_open_calls = 0

    async def call(self, func: Callable) -> Any:
        """
        Execute function through circuit breaker.

        Args:
            func: Async callable to execute

        Returns:
            Result from func

        Raises:
            CircuitBreakerOpenError: If circuit is open
            Any exception raised by func
        """
        # Check if circuit should transition from OPEN to HALF_OPEN
        if self.state == CircuitState.OPEN:
            if self.last_failure_time and \
               datetime.now() - self.last_failure_time > timedelta(seconds=self.timeout):
                logger.info("Circuit breaker transitioning to HALF_OPEN")
                self.state = CircuitState.HALF_OPEN
                self.half_open_calls = 0
            else:
                time_remaining = self.timeout
                if self.last_failure_time:
                    elapsed = (datetime.now() - self.last_failure_time).total_seconds()
                    time_remaining = max(0, self.timeout - elapsed)

                raise CircuitBreakerOpenError(
                    f"Circuit breaker is OPEN. Too many failures. "
                    f"Retry after {time_remaining:.0f}s."
                )

        # Limit calls in HALF_OPEN state
        if self.state == CircuitState.HALF_OPEN:
            if self.half_open_calls >= self.half_open_max_calls:
                raise CircuitBreakerOpenError(
                    "Circuit breaker is HALF_OPEN. Test call already in progress."
                )
            self.half_open_calls += 1

        try:
            result = await func() if asyncio.iscoroutinefunction(func) else func()
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    def _on_success(self):
        """Handle successful call"""
        if self.state == CircuitState.HALF_OPEN:
            logger.info("Circuit breaker transitioning to CLOSED (recovery successful)")
            self.state = CircuitState.CLOSED

        self.failure_count = 0
        self.last_failure_time = None

    def _on_failure(self):
        """Handle failed call"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        if self.state == CircuitState.HALF_OPEN:
            logger.warning("Circuit breaker transitioning to OPEN (recovery failed)")
            self.state = CircuitState.OPEN
            return

        if self.failure_count >= self.failure_threshold:
            logger.warning(
                f"Circuit breaker transitioning to OPEN "
                f"({self.failure_count} failures reached threshold)"
            )
            self.state = CircuitState.OPEN

    def get_state(self) -> CircuitState:
        """Get current circuit state"""
        return self.state

    def reset(self):
        """Manually reset circuit to CLOSED state"""
        logger.info("Circuit breaker manually reset to CLOSED")
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open and blocking requests"""
    pass


class ErrorClassifier:
    """Classify errors into categories for better handling and user messaging"""

    ERROR_CATEGORIES = {
        'network': {
            'keywords': ['connection', 'timeout', 'network', 'unreachable', 'refused'],
            'types': ['ConnectionError', 'TimeoutError', 'HTTPError', 'RequestException'],
            'retryable': True,
            'user_message': "Network connection issue. Please check your internet connection and try again."
        },
        'permission': {
            'keywords': ['permission', 'access denied', 'forbidden', 'unauthorized'],
            'types': ['PermissionError', 'OSError'],
            'retryable': False,
            'user_message': "Permission denied. Please check file and directory permissions."
        },
        'parsing': {
            'keywords': ['decode', 'encoding', 'utf-8', 'unicode', 'syntax', 'invalid'],
            'types': ['UnicodeDecodeError', 'UnicodeError', 'SyntaxError'],
            'retryable': False,
            'user_message': "Unable to parse file content. The file may be corrupted or in an unsupported encoding."
        },
        'embedding': {
            'keywords': ['embed', 'cohere', 'openai', 'rate limit', 'quota'],
            'types': ['EmbeddingError', 'APIError'],
            'retryable': True,
            'user_message': "Embedding service unavailable. Please try again in a few moments."
        },
        'database': {
            'keywords': ['database', 'supabase', 'postgres', 'sql', 'query', 'constraint'],
            'types': ['DatabaseError', 'IntegrityError', 'OperationalError'],
            'retryable': True,
            'user_message': "Database error occurred. Please contact support if this persists."
        },
        'circuit_breaker': {
            'keywords': ['circuit breaker'],
            'types': ['CircuitBreakerOpenError'],
            'retryable': False,
            'user_message': "Too many recent failures. System is temporarily unavailable."
        }
    }

    @classmethod
    def classify(cls, error: Exception) -> str:
        """
        Classify error into category.

        Args:
            error: Exception to classify

        Returns:
            Category name: 'network', 'permission', 'parsing', 'embedding',
                          'database', 'circuit_breaker', or 'unknown'
        """
        error_str = str(error).lower()
        error_type = type(error).__name__

        # Check each category
        for category, config in cls.ERROR_CATEGORIES.items():
            # Check error type name
            if error_type in config['types']:
                return category

            # Check keywords in error message
            if any(keyword in error_str for keyword in config['keywords']):
                return category

        return 'unknown'

    @classmethod
    def is_retryable(cls, error_type: str) -> bool:
        """
        Determine if error type is retryable.

        Args:
            error_type: Error category name

        Returns:
            True if error should be retried
        """
        config = cls.ERROR_CATEGORIES.get(error_type)
        if config:
            return config['retryable']
        return False

    @classmethod
    def get_user_message(cls, error_type: str, error: Exception) -> str:
        """
        Get user-friendly error message.

        Args:
            error_type: Error category name
            error: Original exception

        Returns:
            User-friendly error message
        """
        config = cls.ERROR_CATEGORIES.get(error_type)
        if config:
            message = config['user_message']
            # Add specific error details for certain types
            if error_type in ['permission', 'parsing']:
                message = f"{message} Details: {str(error)}"
            return message

        return f"An unexpected error occurred: {str(error)}"

    @classmethod
    def should_log_full_trace(cls, error_type: str) -> bool:
        """
        Determine if full stack trace should be logged for error type.

        Args:
            error_type: Error category name

        Returns:
            True if full trace should be logged
        """
        # Don't log full trace for common, expected errors
        expected_errors = {'network', 'circuit_breaker'}
        return error_type not in expected_errors


class SyncErrorLogger:
    """Logger for sync errors with database persistence"""

    def __init__(self, db):
        """
        Initialize error logger.

        Args:
            db: Supabase client for database access
        """
        self.db = db

    async def log_error(
        self,
        project_id: Optional[str],
        error_type: str,
        error_message: str,
        error_details: Dict,
        file_path: Optional[str] = None,
        retry_count: int = 0
    ) -> Optional[str]:
        """
        Log sync error to database.

        Args:
            project_id: Project UUID (nullable)
            error_type: Error category
            error_message: Error message
            error_details: Additional context (stack trace, etc.)
            file_path: File path if error relates to specific file
            retry_count: Number of retries attempted

        Returns:
            Error log ID if successful, None if logging failed
        """
        try:
            result = await self.db.table('sync_error_log').insert({
                'project_id': project_id,
                'error_type': error_type,
                'error_message': error_message,
                'error_details': error_details,
                'file_path': file_path,
                'retry_count': retry_count,
                'resolved': False
            }).execute()

            if result.data:
                return result.data[0].get('id')

            return None

        except Exception as e:
            # Don't fail sync operation if error logging fails
            logger.error(f"Failed to log sync error to database: {e}")
            return None

    async def mark_resolved(self, error_log_id: str):
        """
        Mark error as resolved.

        Args:
            error_log_id: Error log UUID
        """
        try:
            await self.db.table('sync_error_log')\
                .update({'resolved': True})\
                .eq('id', error_log_id)\
                .execute()
        except Exception as e:
            logger.error(f"Failed to mark error as resolved: {e}")

    async def get_recent_errors(
        self,
        project_id: str,
        limit: int = 10
    ) -> list:
        """
        Get recent errors for a project.

        Args:
            project_id: Project UUID
            limit: Maximum number of errors to return

        Returns:
            List of recent error records
        """
        try:
            result = await self.db.table('sync_error_log')\
                .select('*')\
                .eq('project_id', project_id)\
                .order('occurred_at', desc=True)\
                .limit(limit)\
                .execute()

            return result.data if result.data else []

        except Exception as e:
            logger.error(f"Failed to fetch recent errors: {e}")
            return []


def handle_sync_error(
    error: Exception,
    context: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Handle sync error with classification and structured response.

    Args:
        error: Exception that occurred
        context: Context information (project_id, file_path, etc.)

    Returns:
        Dict with error information:
        {
            'error_type': str,
            'error_message': str,
            'user_message': str,
            'retryable': bool,
            'context': dict
        }
    """
    error_type = ErrorClassifier.classify(error)
    user_message = ErrorClassifier.get_user_message(error_type, error)
    retryable = ErrorClassifier.is_retryable(error_type)
    log_trace = ErrorClassifier.should_log_full_trace(error_type)

    # Log appropriately
    if log_trace:
        logger.error(
            f"Sync error ({error_type}): {error}",
            exc_info=True,
            extra=context
        )
    else:
        logger.warning(
            f"Sync error ({error_type}): {error}",
            extra=context
        )

    return {
        'error_type': error_type,
        'error_message': str(error),
        'user_message': user_message,
        'retryable': retryable,
        'context': context
    }
