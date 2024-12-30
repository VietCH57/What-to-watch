import requests
from bs4 import BeautifulSoup
import time
from urllib.parse import quote_plus
import os
import hashlib
from datetime import datetime, timedelta

from .cache import Cache

class PosterCache:
    def __init__(self, image_dir="D:\\Programming\\What To Watch\\wtwData\\images"):
        self.image_dir = image_dir
        # Create directory if it doesn't exist
        os.makedirs(self.image_dir, exist_ok=True)

    def get_image_path(self, title, year):
        # Create a unique filename based on title and year
        filename = f"{title}_{year if year else 'no_year'}"
        # Hash the filename to ensure it's filesystem-safe
        hashed_name = hashlib.md5(filename.encode()).hexdigest()
        return os.path.join(self.image_dir, f"{hashed_name}.jpg")

    def get(self, title, year):
        image_path = self.get_image_path(title, year)
        if os.path.exists(image_path):
            return image_path
        return None

    def save(self, title, year, image_data):
        image_path = self.get_image_path(title, year)
        with open(image_path, 'wb') as f:
            f.write(image_data)
        return image_path

class PosterScraper:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.search_delay = 1
        self.last_search = 0
        self.cache = PosterCache()

    def get_poster_url(self, title, year=None):
        try:
            # Check local cache first
            cached_path = self.cache.get(title, year)
            if cached_path:
                return cached_path

            # Respect rate limiting
            current_time = time.time()
            time_since_last = current_time - self.last_search
            if time_since_last < self.search_delay:
                time.sleep(self.search_delay - time_since_last)
            
            # Format search query
            search_query = f"{title} {year if year else ''} movie poster"
            encoded_query = quote_plus(search_query)
            search_url = f"https://www.google.com/search?q={encoded_query}&tbm=isch"
            
            # Make request
            response = requests.get(search_url, headers=self.headers)
            if response.status_code != 200:
                return None
            
            # Parse response
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find image URLs
            img_elements = soup.find_all('img')
            
            # Skip the first image and get the next valid one
            if len(img_elements) > 1:
                for img in img_elements[1:]:
                    src = img.get('src')
                    if src and self._is_valid_image_url(src):
                        # Download and save the image
                        try:
                            img_response = requests.get(src, headers=self.headers)
                            if img_response.status_code == 200:
                                # Save the image locally
                                saved_path = self.cache.save(title, year, img_response.content)
                                self.last_search = time.time()
                                return saved_path
                        except Exception as e:
                            print(f"Error downloading image: {str(e)}")
                            continue
            
            return None

        except Exception as e:
            print(f"Error finding poster for {title}: {str(e)}")
            return None

    def _is_valid_image_url(self, url):
        image_extensions = ('.jpg', '.jpeg', '.png', '.webp')
        if url.startswith('data:image'):
            return False
        if 'icon' in url.lower():
            return False
        return any(url.lower().endswith(ext) for ext in image_extensions)