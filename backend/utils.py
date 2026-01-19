import time
import random
import functools
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def retry_with_backoff(retries=3, backoff_in_seconds=1, maximize_jitter=False):
    """
    Decorator to retry a function with exponential backoff and jitter.
    
    Args:
        retries (int): Maximum number of retries.
        backoff_in_seconds (int): Initial backoff time in seconds.
        maximize_jitter (bool): If True, jitter will be between 0 and full backoff time.
                                If False, jitter will be small random addition.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            x = 0
            while True:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if x == retries:
                        logger.error(f"Function {func.__name__} failed after {retries} retries. Final error: {e}")
                        raise
                    
                    sleep = (backoff_in_seconds * 2 ** min(x, 6))
                    
                    if maximize_jitter:
                         # Full jitter: random between 0 and sleep
                         sleep = random.uniform(0, sleep)
                    else:
                         # Small jitter: sleep + random small amount
                         sleep = sleep + random.uniform(0, 1)
                    
                    logger.warning(f"Error in {func.__name__}: {e}. Retrying in {sleep:.2f}s... (Attempt {x+1}/{retries})")
                    time.sleep(sleep)
                    x += 1
        return wrapper
    return decorator
