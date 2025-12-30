import redis
import json
import os

def inspect_cache():
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    r = redis.from_url(redis_url, decode_responses=True)
    
    # Get all keys
    keys = r.keys("climate:current:*")
    print(f"✅ Connected to Redis at {redis_url}")
    print(f"📊 Total cached grid points: {len(keys)}")
    
    if keys:
        # Show a sample
        sample_key = keys[0]
        data = json.loads(r.get(sample_key))
        print(f"\n🔍 Sample Data Point ({sample_key}):")
        print(json.dumps(data, indent=2))
        
        # Check for PM2.5 specifically
        pm25_count = sum(1 for k in keys if json.loads(r.get(k)).get('pm25') is not None)
        print(f"\n🌫️  Points with PM2.5 data: {pm25_count}/{len(keys)}")
    else:
        print("\n⚠️ Cache is empty. Run the fetcher first.")

if __name__ == "__main__":
    inspect_cache()
