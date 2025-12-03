"""Unit test: Idempotency cache."""
import pytest
import time
from src.resilience.cache import IdempotencyCache


def test_cache_miss():
    """Test cache miss returns None."""
    cache = IdempotencyCache()
    
    result = cache.get("request-123", "graph-1", "A", "B")
    
    assert result is None


def test_cache_hit():
    """Test cache hit returns stored value."""
    cache = IdempotencyCache()
    
    request_id = "request-123"
    expected_result = {"path": ["A", "B"], "cost": 5.0}
    
    cache.put(request_id, expected_result, graph_id="graph-1", start="A", goal="B")
    
    result = cache.get(request_id, graph_id="graph-1", start="A", goal="B")
    
    assert result == expected_result


def test_cache_ttl_expiration():
    """Test cache entries expire after TTL."""
    cache = IdempotencyCache(default_ttl=0.1)  # 100ms TTL
    
    request_id = "request-123"
    cache.put(request_id, "result", graph_id="graph-1", start="A", goal="B")
    
    # Immediately: should hit
    assert cache.get(request_id, graph_id="graph-1", start="A", goal="B") == "result"
    
    # After TTL: should miss
    time.sleep(0.2)
    assert cache.get(request_id, graph_id="graph-1", start="A", goal="B") is None


def test_cache_lru_eviction():
    """Test LRU eviction when cache is full."""
    cache = IdempotencyCache(maxsize=2)
    
    cache.put("req-1", "result-1", graph_id="g1")
    cache.put("req-2", "result-2", graph_id="g2")
    
    # Cache full, next put should evict req-1 (LRU)
    cache.put("req-3", "result-3", graph_id="g3")
    
    # req-1 should be evicted
    assert cache.get("req-1", graph_id="g1") is None
    
    # req-2 and req-3 should still be present
    assert cache.get("req-2", graph_id="g2") == "result-2"
    assert cache.get("req-3", graph_id="g3") == "result-3"


def test_cache_stats():
    """Test cache statistics."""
    cache = IdempotencyCache(maxsize=10)
    
    cache.put("req-1", "result-1", graph_id="g1")
    cache.put("req-2", "result-2", graph_id="g2")
    
    stats = cache.stats()
    
    assert stats["size"] == 2
    assert stats["maxsize"] == 10
    assert stats["utilization"] == 0.2
