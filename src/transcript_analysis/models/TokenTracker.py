from dataclasses import dataclass
import logging
from threading import Lock

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)



@dataclass
class TokenUsage:
    """Track token usage, costs, and timing across API calls"""
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost: float = 0.0
    total_time: float = 0.0  # Total execution time in seconds
    call_count: int = 0
    min_time: float = float('inf')  # Fastest call
    max_time: float = 0.0  # Slowest call

class TokenTracker:
    _instance = None
    _instance_lock = Lock()

    def __new__(cls):
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = super(TokenTracker, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        # Ensure __init__ is only called once
        if hasattr(self, '_initialized') and self._initialized:
            return
        self.usage = TokenUsage()
        self.lock = Lock()
        self._initialized = True



    def update(self, input_tokens: int, output_tokens: int, cost: float, call_time: float) -> None:
        """Update token usage and timing metrics."""
        with self.lock:
            self.usage.total_input_tokens += input_tokens
            self.usage.total_output_tokens += output_tokens
            self.usage.total_cost += cost
            self.usage.total_time += call_time
            self.usage.call_count += 1
            self.usage.min_time = min(self.usage.min_time, call_time)
            self.usage.max_time = max(self.usage.max_time, call_time)
    
    def summary(self) -> None:
        """Log cumulative token usage, cost, and timing summary."""
        with self.lock:
            avg_time = self.usage.total_time / self.usage.call_count if self.usage.call_count > 0 else 0
            logger.info("\n" + "="*60)
            logger.info("BEDROCK API USAGE SUMMARY")
            logger.info("="*60)
            logger.info(f"Total API Calls: {self.usage.call_count}")
            logger.info(f"Total Input Tokens: {self.usage.total_input_tokens:,}")
            logger.info(f"Total Output Tokens: {self.usage.total_output_tokens:,}")
            logger.info(f"Total Tokens: {self.usage.total_input_tokens + self.usage.total_output_tokens:,}")
            logger.info(f"Total Cost: ${self.usage.total_cost:.4f}")
            logger.info("-" * 60)
            logger.info("TIMING STATISTICS:")
            logger.info(f"Total Time: {self.usage.total_time:.2f} seconds")
            logger.info(f"Average Time per Call: {avg_time:.2f} seconds")
            if self.usage.call_count > 0:
                logger.info(f"Fastest Call: {self.usage.min_time:.2f} seconds")
                logger.info(f"Slowest Call: {self.usage.max_time:.2f} seconds")
            logger.info("="*60)
    
    def reset(self) -> None:
        """Reset token tracker for a new session."""
        with self.lock:
            self.usage = TokenUsage()
    
token_tracker = TokenTracker()