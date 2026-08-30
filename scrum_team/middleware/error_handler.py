import time
import logging
from typing import Callable, Any, Dict, Optional

logger = logging.getLogger(__name__)

class GraphExecutionError(Exception):
    """Controlled exception for graph node errors."""
    pass

def execute_with_retry(
    fn: Callable[[], Any],
    max_retries: int = 2,
    initial_delay: float = 0.5,
    log_callback: Optional[Callable[[str], None]] = None,
    task_name: str = "LLM Operation"
) -> Any:
    """
    Executes a function with exponential backoff retries for transient connection,
    timeout, or parsing failures.
    """
    delay = initial_delay
    last_exception = None

    for attempt in range(1, max_retries + 2):
        try:
            return fn()
        except Exception as e:
            last_exception = e
            error_msg = str(e)
            
            if attempt <= max_retries:
                log_msg = f"[Retry {attempt}/{max_retries}] {task_name} encountered error: '{error_msg[:120]}'. Retrying in {delay:.1f}s..."
                logger.warning(log_msg)
                if log_callback:
                    log_callback(log_msg)
                time.sleep(delay)
                delay *= 1.5
            else:
                final_log = f"[Unrecoverable Error] {task_name} failed after {max_retries} retries: '{error_msg[:150]}'."
                logger.error(final_log)
                if log_callback:
                    log_callback(final_log)

    raise GraphExecutionError(f"{task_name} failed after {max_retries} retries: {last_exception}")

def safe_node_execution(
    node_name: str,
    node_fn: Callable[[Dict[str, Any]], Dict[str, Any]],
    state: Dict[str, Any],
    log_callback: Optional[Callable[[str], None]] = None
) -> Dict[str, Any]:
    """
    Middleware wrapper around graph node executions to catch unexpected exceptions,
    log failure details clearly, and return a clean error state rather than crashing.
    """
    try:
        return node_fn(state)
    except Exception as e:
        error_details = f"Node '{node_name}' failed with error: {str(e)}"
        logger.error(error_details, exc_info=True)
        
        if log_callback:
            log_callback(f"⚠️ [Node Error] {error_details}")
            
        return {
            "status": "error_paused",
            "last_error": error_details,
            "error_node": node_name
        }
