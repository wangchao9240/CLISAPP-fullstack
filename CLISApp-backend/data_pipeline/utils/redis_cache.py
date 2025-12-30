"""
Redis缓存管理工具
"""
import redis
import json
from typing import Optional, Dict, List
from datetime import datetime, timedelta
import os

class ClimateDataCache:
    """气候数据Redis缓存"""

    def __init__(self, redis_url: str = None):
        if redis_url is None:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.redis = redis.from_url(redis_url, decode_responses=True)

    def cache_point_data(self, key: str, data: Dict, ttl: int = 3600):
        """缓存单个点的数据"""
        self.redis.setex(key, ttl, json.dumps(data))

    def get_point_data(self, key: str) -> Optional[Dict]:
        """获取缓存的点数据"""
        data = self.redis.get(key)
        return json.loads(data) if data else None

    def cache_all_points(self, points_data: Dict[str, Dict], ttl: int = 3600):
        """批量缓存所有点数据"""
        pipe = self.redis.pipeline()
        for key, data in points_data.items():
            cache_key = f"climate:current:{key}"
            pipe.setex(cache_key, ttl, json.dumps(data))
        pipe.set("climate:last_update", datetime.now().isoformat())
        pipe.execute()

    def get_all_points(self) -> Dict[str, Dict]:
        """获取所有缓存的点数据"""
        keys = self.redis.keys("climate:current:*")
        if not keys:
            return {}

        pipe = self.redis.pipeline()
        for key in keys:
            pipe.get(key)

        results = {}
        for key, data in zip(keys, pipe.execute()):
            if data:
                coord_key = key.replace("climate:current:", "")
                results[coord_key] = json.loads(data)

        return results

    def get_last_update(self) -> Optional[str]:
        """获取最后更新时间"""
        return self.redis.get("climate:last_update")

    def clear_cache(self):
        """清空所有缓存"""
        keys = self.redis.keys("climate:*")
        if keys:
            self.redis.delete(*keys)
