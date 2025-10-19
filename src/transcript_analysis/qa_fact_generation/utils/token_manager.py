"""
Token management utilities for evaluation system.
"""
import logging
from typing import List, Tuple, Optional

logger = logging.getLogger(__name__)


class TokenManager:
    """Handles token counting and text truncation for LLM prompts."""
    
    def __init__(self, max_prompt_tokens: int = 7000, response_tokens: int = 1000):
        self.max_prompt_tokens = max_prompt_tokens
        self.response_tokens = response_tokens
        self.logger = logging.getLogger(__name__)
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text using approximation."""
        # Rough approximation: 1 token ≈ 4 characters
        return len(text) // 4
    
    def calculate_available_tokens(self, base_prompt: str) -> int:
        """Calculate tokens available for nuggets given base prompt."""
        base_tokens = self.count_tokens(base_prompt)
        available = self.max_prompt_tokens - base_tokens - self.response_tokens
        return max(0, available)
    
    def truncate_nuggets_for_prompt(
        self, 
        nuggets: List[str], 
        summary: str, 
        prompt_template: str,
        max_nuggets: Optional[int] = None,
        strategy: str = "first_n"
    ) -> Tuple[List[str], bool]:
        """
        Truncate nuggets to fit within token limits.
        
        Args:
            nuggets: List of nugget texts
            summary: Summary text
            prompt_template: Template for the prompt (with placeholder for nuggets)
            max_nuggets: Maximum number of nuggets to include
            strategy: Truncation strategy ('first_n', 'sample', 'shortest_first')
            
        Returns:
            Tuple of (truncated_nuggets, was_truncated)
        """
        if not nuggets:
            return [], False
            
        # Calculate base prompt tokens (without nuggets)
        base_prompt = prompt_template.replace("{nuggets}", "").replace("{summary}", summary)
        available_tokens = self.calculate_available_tokens(base_prompt)
        
        if available_tokens <= 0:
            self.logger.warning("Base prompt too long, severe truncation required")
            return nuggets[:1], True
        
        # Apply truncation strategy
        if strategy == "first_n":
            return self._truncate_first_n(nuggets, available_tokens, max_nuggets)
        elif strategy == "sample":
            return self._truncate_sample(nuggets, available_tokens, max_nuggets)
        elif strategy == "shortest_first":
            return self._truncate_shortest_first(nuggets, available_tokens, max_nuggets)
        else:
            return self._truncate_first_n(nuggets, available_tokens, max_nuggets)
    
    def _truncate_first_n(
        self, 
        nuggets: List[str], 
        available_tokens: int, 
        max_nuggets: Optional[int]
    ) -> Tuple[List[str], bool]:
        """Keep first N nuggets within token limits."""
        truncated_nuggets = []
        current_tokens = 0
        was_truncated = False
        
        for i, nugget in enumerate(nuggets):
            nugget_tokens = self.count_tokens(nugget)
            
            # Check token limit
            if current_tokens + nugget_tokens > available_tokens:
                was_truncated = True
                break
                
            # Check max_nuggets limit
            if max_nuggets and len(truncated_nuggets) >= max_nuggets:
                was_truncated = True
                break
                
            truncated_nuggets.append(nugget)
            current_tokens += nugget_tokens
        
        # Log truncation info
        if was_truncated:
            self.logger.info(
                f"Truncated nuggets from {len(nuggets)} to {len(truncated_nuggets)} "
                f"to fit within {available_tokens} tokens"
            )
        
        return truncated_nuggets, was_truncated
    
    def _truncate_sample(
        self, 
        nuggets: List[str], 
        available_tokens: int, 
        max_nuggets: Optional[int]
    ) -> Tuple[List[str], bool]:
        """Sample nuggets evenly across the full list."""
        target_count = min(max_nuggets or 20, len(nuggets))
        
        # First try with target count
        if len(nuggets) <= target_count:
            return self._truncate_first_n(nuggets, available_tokens, max_nuggets)
        
        # Sample evenly
        step = len(nuggets) // target_count
        sampled = [nuggets[i] for i in range(0, len(nuggets), step)][:target_count]
        
        return self._truncate_first_n(sampled, available_tokens, max_nuggets)
    
    def _truncate_shortest_first(
        self, 
        nuggets: List[str], 
        available_tokens: int, 
        max_nuggets: Optional[int]
    ) -> Tuple[List[str], bool]:
        """Prioritize shorter nuggets to include more of them."""
        sorted_nuggets = sorted(nuggets, key=len)
        return self._truncate_first_n(sorted_nuggets, available_tokens, max_nuggets)
    
    def estimate_chunks_needed(self, content: str, chunk_size: int = 4000) -> int:
        """Estimate how many chunks will be needed for content."""
        content_tokens = self.count_tokens(content)
        return (content_tokens + chunk_size - 1) // chunk_size  # Ceiling division

