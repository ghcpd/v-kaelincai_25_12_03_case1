"""Idempotency cache for request deduplication."""
import time
import hashlib
import logging
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Cache entry with result and metadata."""
    request_id: str
    result: Any
    timestamp: float
    ttl: float
    
    def is_expired(self) -> bool:
        """Check if entry has expired."""
        return time.time() - self.timestamp > self.ttl


class IdempotencyCache:
    """
    LRU cache for request idempotency.
    
    Ensures duplicate requests return cached results.
    """
    
    def __init__(self, maxsize: int = 1000, default_ttl: float = 300.0):
        """
        Initialize cache.
        
        Args:
            maxsize: Maximum number of entries
            default_ttl: Default time-to-live in seconds (5 minutes)
        """
        self.maxsize = maxsize
        self.default_ttl = default_ttl
        self._cache: Dict[str, CacheEntry] = {}
        self._access_order: list = []  # For LRU eviction
    
    def get(self, request_id: str, *args, **kwargs) -> Optional[Any]:
        """
        Get cached result for request.
        
        Args:
            request_id: Unique request identifier
            *args, **kwargs: Additional cache key components
            
        Returns:
            Cached result if found and not expired, else None
        """
        cache_key = self._make_key(request_id, *args, **kwargs)
        
        if cache_key in self._cache:
            entry = self._cache[cache_key]
            
            if entry.is_expired():
                logger.debug(f"Cache entry expired: {request_id}")
                del self._cache[cache_key]
                self._access_order.remove(cache_key)
                return None
            
            # Update access order (LRU)
            self._access_order.remove(cache_key)
            self._access_order.append(cache_key)
            
            logger.info(f"Cache hit: {request_id}")
            return entry.result
        
        return None
    
    def put(
        self, 
        request_id: str, 
        result: Any, 
        ttl: Optional[float] = None,
        *args,
        **kwargs
    ):
        """
        Store result in cache.
        
        Args:
            request_id: Unique request identifier
            result: Result to cache
            ttl: Time-to-live override
            *args, **kwargs: Additional cache key components
        """
        cache_key = self._make_key(request_id, *args, **kwargs)
        
        # Evict oldest entry if at capacity
        if len(self._cache) >= self.maxsize and cache_key not in self._cache:
            self._evict_lru()
        
        entry = CacheEntry(
            request_id=request_id,
            result=result,
            timestamp=time.time(),
            ttl=ttl or self.default_ttl
        )
        
        self._cache[cache_key] = entry
        
        # Update access order
        if cache_key in self._access_order:
            self._access_order.remove(cache_key)
        self._access_order.append(cache_key)
        
        logger.debug(f"Cached result: {request_id}")
    
    def _make_key(self, request_id: str, *args, **kwargs) -> str:
        """
        Generate cache key from request_id and additional parameters.
        
        Includes all inputs to ensure cache correctness.
        """
        # Combine request_id with args/kwargs for complete key
        key_parts = [request_id]
        key_parts.extend(str(arg) for arg in args)
        key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
        
        key_str = "|".join(key_parts)
        # Hash for fixed-length key
        return hashlib.sha256(key_str.encode()).hexdigest()
    
    def _evict_lru(self):
        """Evict least recently used entry."""
        if not self._access_order:
            return
        
        lru_key = self._access_order.pop(0)
        if lru_key in self._cache:
            entry = self._cache[lru_key]
            logger.debug(f"Evicted LRU entry: {entry.request_id}")
            del self._cache[lru_key]
    
    def clear(self):
        """Clear all cache entries."""
        self._cache.clear()
        self._access_order.clear()
        logger.info("Cache cleared")
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "size": len(self._cache),
            "maxsize": self.maxsize,
            "utilization": len(self._cache) / self.maxsize if self.maxsize > 0 else 0
        }
