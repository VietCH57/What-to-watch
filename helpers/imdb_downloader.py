import os
import gzip
import shutil
import requests
from datetime import datetime
import logging
from pathlib import Path
import time

class IMDbDatasetDownloader:
    def __init__(self):
        # Base directory for data storage
        self.data_dir = Path('D:/Programming/What To Watch/wtwData/data')
        self.data_dir.mkdir(exist_ok=True)
        
        # Create log directory with subdirectory
        self.log_dir = Path('D:/Programming/What To Watch/wtwData/log/download')
        self.log_dir.mkdir(parents=True, exist_ok=True)  # parents=True ensures all parent directories are created
        
        # Setup logging with new log directory
        logging.basicConfig(
            filename=self.log_dir / 'imdb_download.log',
            level=logging.INFO,
            format='%(asctime)s - %(message)s'
        )
        
        # IMDb dataset URLs
        self.datasets = {
            'title.basics': 'https://datasets.imdbws.com/title.basics.tsv.gz',
            'name.basics': 'https://datasets.imdbws.com/name.basics.tsv.gz',
            'title.ratings': 'https://datasets.imdbws.com/title.ratings.tsv.gz',
            'title.crew': 'https://datasets.imdbws.com/title.crew.tsv.gz',
            'title.principals': 'https://datasets.imdbws.com/title.principals.tsv.gz'
        }
        
        # Last update tracker file (kept in data directory)
        self.last_update_file = self.data_dir / 'last_update.txt'

    def need_update(self):
        """Check if we need to update the datasets"""
        if not self.last_update_file.exists():
            return True
            
        with open(self.last_update_file, 'r') as f:
            last_update = datetime.fromisoformat(f.read().strip())
            current_time = datetime.now()
            # Update if more than 24 hours have passed
            return (current_time - last_update).days >= 1

    def download_file(self, url, filename):
        """Download a file with progress tracking"""
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            file_path = self.data_dir / filename
            
            logging.info(f"Downloading {filename}")
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            logging.info(f"Successfully downloaded {filename}")
            return True
            
        except Exception as e:
            logging.error(f"Error downloading {filename}: {str(e)}")
            return False

    def update_datasets(self):
        """Download and update all datasets"""
        if not self.need_update():
            logging.info("Datasets are up to date")
            return
        
        success = True
        for name, url in self.datasets.items():
            filename = f"{name}.tsv.gz"
            if not self.download_file(url, filename):
                success = False
                break
                
        if success:
            # Update the last update timestamp
            with open(self.last_update_file, 'w') as f:
                f.write(datetime.now().isoformat())
            logging.info("All datasets successfully updated")
        else:
            logging.error("Failed to update all datasets")

def main():
    downloader = IMDbDatasetDownloader()
    while True:
        try:
            downloader.update_datasets()
            # Wait for 24 hours before checking again
            time.sleep(24 * 60 * 60)
        except KeyboardInterrupt:
            logging.info("Download service stopped by user")
            break
        except Exception as e:
            logging.error(f"Unexpected error: {str(e)}")
            # Wait 1 hour before retrying in case of error
            time.sleep(60 * 60)

if __name__ == "__main__":
    main()