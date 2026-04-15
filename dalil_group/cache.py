#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Redis Caching Layer
===================

Caching service for frequently accessed data using Redis.
"""

import os
import json
import logging
from typing import Optional, Any, List
from datetime import timedelta
import redis
from functools import wraps

logger = logging.getLogger(__name__)

# Redis connection pool
redis_host = os.environ.get("REDIS_HOST", "localhost")
redis_port = int(os.environ.get("REDIS_PORT", 6379))
redis_db = int(os.environ.get("REDIS_DB", 0))

try:
    redis_client = redis.Redis(
        host=redis_host,
        port=redis_port,
        db=redis_db,
        decode_responses=True,
        socket_connect_timeout=5,
    )
    # Test connection
    redis_client.ping()
    logger.info(f"[+] Connected to Redis at {redis_host}:{redis_port}")
    REDIS_AVAILABLE = True
except Exception as e:
    logger.warning(f"[!] Redis connection failed: {e}. Caching disabled.")
    REDIS_AVAILABLE = False
    redis_client = None


class CacheKey:
    """Cache key constants."""

    # Evaluation cache keys
    EVALUATION = "eval:{project_id}"
    EVALUATION_RESULTS = "eval:results:{project_id}"
    EVALUATION_PROMPTS = "eval:prompts:{project_id}"
    
    # User cache keys
    USER = "user:{user_id}"
    USER_EVALUATIONS = "user:evals:{user_id}"
    
    # Batch job cache keys
    BATCH_JOB = "batch:{job_id}"
    USER_BATCH_JOBS = "batch:user:{user_id}"
    
    # Model response cache
    MODEL_RESPONSES = "responses:{evaluation_id}:{prompt_id}"
    
    # Config preset cache
    CONFIG_PRESET = "preset:{preset_id}"
    USER_PRESETS = "presets:user:{user_id}"
    
    # Statistics cache
    STATS_EVALUATION = "stats:eval:{evaluation_id}"
    STATS_USER = "stats:user:{user_id}"
    
    # LLM provider cache
    OLLAMA_MODELS = "ollama:models"
    AVAILABLE_MODELS = "available:models"


def cache_get(key: str) -> Optional[Any]:
    """Get value from cache."""
    if not REDIS_AVAILABLE or not redis_client:
        return None
    
    try:
        value = redis_client.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
    except Exception as e:
        logger.warning(f"Cache get error for {key}: {e}")
    
    return None


def cache_set(
    key: str,
    value: Any,
    ttl: int = 3600,  # 1 hour default
) -> bool:
    """Set value in cache with TTL."""
    if not REDIS_AVAILABLE or not redis_client:
        return False
    
    try:
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        
        redis_client.setex(key, ttl, value)
        return True
    except Exception as e:
        logger.warning(f"Cache set error for {key}: {e}")
    
    return False


def cache_delete(key: str) -> bool:
    """Delete key from cache."""
    if not REDIS_AVAILABLE or not redis_client:
        return False
    
    try:
        redis_client.delete(key)
        return True
    except Exception as e:
        logger.warning(f"Cache delete error for {key}: {e}")
    
    return False


def cache_delete_pattern(pattern: str) -> int:
    """Delete all keys matching pattern."""
    if not REDIS_AVAILABLE or not redis_client:
        return 0
    
    try:
        keys = redis_client.keys(pattern)
        if keys:
            return redis_client.delete(*keys)
        return 0
    except Exception as e:
        logger.warning(f"Cache delete pattern error for {pattern}: {e}")
    
    return 0


def cache_invalidate_evaluation(project_id: str) -> None:
    """Invalidate all caches related to an evaluation."""
    if not REDIS_AVAILABLE:
        return
    
    patterns = [
        CacheKey.EVALUATION.replace("{project_id}", project_id),
        CacheKey.EVALUATION_RESULTS.replace("{project_id}", project_id),
        CacheKey.EVALUATION_PROMPTS.replace("{project_id}", project_id),
        f"responses:{project_id}:*",
    ]
    
    for pattern in patterns:
        cache_delete_pattern(pattern)


def cache_invalidate_user(user_id: int) -> None:
    """Invalidate all caches related to a user."""
    if not REDIS_AVAILABLE:
        return
    
    patterns = [
        CacheKey.USER.replace("{user_id}", str(user_id)),
        CacheKey.USER_EVALUATIONS.replace("{user_id}", str(user_id)),
        CacheKey.USER_BATCH_JOBS.replace("{user_id}", str(user_id)),
        CacheKey.USER_PRESETS.replace("{user_id}", str(user_id)),
        CacheKey.STATS_USER.replace("{user_id}", str(user_id)),
    ]
    
    for pattern in patterns:
        cache_delete_pattern(pattern)


def cached(ttl: int = 3600, key_func=None):
    """Decorator for caching function results.
    
    Args:
        ttl: Time to live in seconds
        key_func: Function to generate cache key from args/kwargs
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # Default: use function name and kwargs
                cache_key = f"{func.__name__}:{json.dumps(kwargs, default=str, sort_keys=True)}"
            
            # Try to get from cache
            cached_value = cache_get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache hit: {cache_key}")
                return cached_value
            
            # Execute function
            result = func(*args, **kwargs)
            
            # Cache result
            if result is not None:
                cache_set(cache_key, result, ttl=ttl)
            
            return result
        
        return wrapper
    return decorator


def get_evaluation_stats(evaluation_id: int, db_func) -> dict:
    """Get evaluation statistics with caching."""
    cache_key = CacheKey.STATS_EVALUATION.replace("{evaluation_id}", str(evaluation_id))
    
    # Try cache first
    cached_stats = cache_get(cache_key)
    if cached_stats:
        return cached_stats
    
    # Compute stats
    stats = db_func(evaluation_id)
    
    # Cache for 1 hour
    cache_set(cache_key, stats, ttl=3600)
    
    return stats


def clear_all_caches() -> None:
    """Clear all caches."""
    if not REDIS_AVAILABLE or not redis_client:
        return
    
    try:
        redis_client.flushdb()
        logger.info("All caches cleared")
    except Exception as e:
        logger.warning(f"Error clearing caches: {e}")


def get_cache_stats() -> dict:
    """Get Redis cache statistics."""
    if not REDIS_AVAILABLE or not redis_client:
        return {"status": "unavailable"}
    
    try:
        info = redis_client.info()
        return {
            "status": "connected",
            "used_memory_human": info.get("used_memory_human"),
            "used_memory_peak_human": info.get("used_memory_peak_human"),
            "connected_clients": info.get("connected_clients"),
            "total_commands_processed": info.get("total_commands_processed"),
            "uptime_in_seconds": info.get("uptime_in_seconds"),
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


# Cache warming functions


def warm_cache() -> None:
    """Pre-populate cache with frequently accessed data."""
    if not REDIS_AVAILABLE:
        return
    
    logger.info("Warming cache...")
    # This would be called on application startup
    # Implement specific warming logic as needed
    pass
