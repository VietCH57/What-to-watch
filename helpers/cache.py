# helpers/cache.py

import os
import json
from datetime import datetime, timedelta

class Cache:
    def __init__(self, cache_dir="D:\\Programming\\What To Watch\\wtwData\\cache"):
        self.cache_dir = cache_dir
        self.cache_file = os.path.join(cache_dir, 'poster_cache.json')
        self.expiry = timedelta(days=7)  # Cache entries expire after 7 days
        
        # Create cache directory if it doesn't exist
        os.makedirs(cache_dir, exist_ok=True)
        
        # Load existing cache or create new one
        self.load_cache()

    def load_cache(self):
        """Load the cache from file or create a new one if it doesn't exist"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    self.cache = json.load(f)
            else:
                self.cache = {}
        except Exception as e:
            print(f"Error loading cache: {str(e)}")
            self.cache = {}

    def save_cache(self):
        """Save the current cache to file"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, indent=2, default=str)
        except Exception as e:
            print(f"Error saving cache: {str(e)}")

    def get(self, key):
        """
        Get a value from the cache
        Returns None if key doesn't exist or entry has expired
        """
        if key in self.cache:
            entry = self.cache[key]
            timestamp = datetime.fromisoformat(entry['timestamp'])
            
            # Check if entry has expired
            if datetime.now() - timestamp < self.expiry:
                return entry['image_path']
            else:
                # Remove expired entry
                del self.cache[key]
                self.save_cache()
        return None

    def set(self, key, image_path):
        """Add or update a cache entry"""
        self.cache[key] = {
            'image_path': image_path,
            'timestamp': datetime.now().isoformat()
        }
        self.save_cache()

    def cleanup(self):
        """Remove expired entries from cache"""
        current_time = datetime.now()
        expired_keys = []
        
        # Find expired entries
        for key, entry in self.cache.items():
            timestamp = datetime.fromisoformat(entry['timestamp'])
            if current_time - timestamp > self.expiry:
                expired_keys.append(key)
        
        # Remove expired entries
        for key in expired_keys:
            del self.cache[key]
        
        if expired_keys:
            self.save_cache()
            return len(expired_keys)
        return 0

    def generate_key(self, title, year):
        """Generate a cache key from title and year"""
        return f"{title}_{year if year else 'no_year'}"

    def get_stats(self):
        """Get cache statistics"""
        return {
            'total_entries': len(self.cache),
            'cache_file_size': os.path.getsize(self.cache_file) if os.path.exists(self.cache_file) else 0,
            'last_cleanup': self.cache.get('_last_cleanup', 'Never')
        }

    def clear(self):
        """Clear all cache entries"""
        self.cache = {}
        self.save_cache()