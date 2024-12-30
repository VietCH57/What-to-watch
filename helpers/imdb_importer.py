import pandas as pd
import sqlite3
import gzip
from pathlib import Path
import logging
from datetime import datetime

class IMDbDataImporter:
    
    
    def __init__(self):
        print("\n=== Starting IMDb Data Import Process ===")
        # Setup paths
        self.data_dir = Path(r"D:\Programming\What To Watch\wtwData\data")
        self.db_path = Path(r"D:\Programming\What To Watch\wtwData\movies.db")
        
        # Create log directory
        self.log_dir = Path(r"D:\Programming\What To Watch\wtwData\log\import")
        self.log_dir.mkdir(parents=True, exist_ok=True)  # Create directory if it doesn't exist
        
        # Setup logging with new path
        log_file = self.log_dir / f'imdb_import_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
        logging.basicConfig(
            filename=log_file,
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        logging.info("Starting IMDb data import process")
        print(f"Log file created at: {log_file}")
        

    def connect_db(self):
        try:
            conn = sqlite3.connect(self.db_path)
            # Enable foreign keys
            conn.execute("PRAGMA foreign_keys=ON")
            return conn
        except Exception as e:
            error_msg = f"Failed to connect to database: {str(e)}"
            logging.error(error_msg)
            print(f"❌ {error_msg}")
            raise
        

    def clear_tables(self):
        """Clear all existing data from tables"""
        try:
            logging.info("Clearing existing data from tables")
            print("\nStarting to clear existing data...")
            conn = self.connect_db()
            cursor = conn.cursor()
            
            # Temporarily disable foreign key constraints
            cursor.execute("PRAGMA foreign_keys=OFF")
            
            # Clear tables in correct order to handle dependencies
            tables = [
                'media_people',
                'media_genres',
                'ratings',
                'genres',
                'people',
                'media'
            ]
            
            for table in tables:
                logging.info(f"Clearing table: {table}")
                print(f"Clearing table: {table}...")
                cursor.execute(f"DELETE FROM {table}")
            
            # Re-enable foreign key constraints
            cursor.execute("PRAGMA foreign_keys=ON")
            
            conn.commit()
            logging.info("Successfully cleared all tables")
            print("✅ All tables cleared successfully!")
            
        except Exception as e:
            error_msg = f"Error clearing tables: {str(e)}"
            logging.error(error_msg)
            print(f"❌ {error_msg}")
            raise
        finally:
            if conn:
                conn.close()
                

    def import_media(self):
        """Import media data from title.basics.tsv.gz"""
        try:
            logging.info("Starting media import")
            print("\nReading media data...")
            conn = self.connect_db()
            
            with gzip.open(self.data_dir / 'title.basics.tsv.gz', 'rt', encoding='utf-8') as f:
                df = pd.read_csv(f, sep='\t', low_memory=False)
                
                print("Processing media data...")
                # Filter only movies and TV shows
                df = df[df['titleType'].isin(['movie', 'tvMovie', 'tvSeries'])]
                
                # Remove entries with empty titles
                df = df.dropna(subset=['primaryTitle'])
                
                # Map columns to our schema
                media_data = df.rename(columns={
                    'tconst': 'imdb_id',
                    'primaryTitle': 'title',
                    'originalTitle': 'original_title',
                    'titleType': 'type',
                    'startYear': 'year',
                    'runtimeMinutes': 'runtime_minutes',
                })
                
                # Clean up the data
                media_data['type'] = media_data['type'].map({
                    'movie': 'movie',
                    'tvMovie': 'movie',
                    'tvSeries': 'tv'
                })
                
                # Convert year and runtime to integer, handling invalid values
                media_data['year'] = pd.to_numeric(media_data['year'], errors='coerce')
                media_data['runtime_minutes'] = pd.to_numeric(media_data['runtime_minutes'], errors='coerce')
                
                # Fill NULL values with appropriate defaults
                media_data['title'] = media_data['title'].fillna('')  # Ensure no NULL titles
                media_data['original_title'] = media_data['original_title'].fillna('')
                media_data['plot'] = None
                media_data['poster_url'] = None
                
                # Select and order columns according to schema
                columns = ['imdb_id', 'title', 'original_title', 'type', 'year', 
                        'runtime_minutes', 'plot', 'poster_url']
                media_data = media_data[columns]
                
                # Additional data validation
                media_data = media_data[
                    (media_data['imdb_id'].notna()) &  # Ensure imdb_id is not null
                    (media_data['title'].str.len() > 0) &  # Ensure title is not empty
                    (media_data['type'].isin(['movie', 'tv']))  # Ensure valid type
                ]
                
                print(f"Importing {len(media_data)} media records...")
                # Import to database
                media_data.to_sql('media', conn, if_exists='append', index=False)
                
                logging.info(f"Imported {len(media_data)} media entries")
                print("✅ Media import completed successfully!")
                
        except Exception as e:
            error_msg = f"Error importing media: {str(e)}"
            logging.error(error_msg)
            print(f"❌ {error_msg}")
            raise
        finally:
            if conn:
                conn.close()
                

    def import_people(self):
        """Import people data from name.basics.tsv.gz"""
        try:
            logging.info("Starting people import")
            print("\nReading people data...")
            conn = self.connect_db()
            
            with gzip.open(self.data_dir / 'name.basics.tsv.gz', 'rt', encoding='utf-8') as f:
                df = pd.read_csv(f, sep='\t', low_memory=False)
                
                print("Processing people data...")
                # Remove entries with empty names
                df = df.dropna(subset=['primaryName'])
                
                people_data = df.rename(columns={
                    'nconst': 'imdb_id',
                    'primaryName': 'name',
                    'birthYear': 'birth_year',
                    'deathYear': 'death_year',
                    'primaryProfession': 'primary_profession'
                })
                
                # Clean up the data
                people_data['name'] = people_data['name'].fillna('')  # Ensure no NULL names
                people_data['birth_year'] = pd.to_numeric(people_data['birth_year'], errors='coerce')
                people_data['death_year'] = pd.to_numeric(people_data['death_year'], errors='coerce')
                people_data['primary_profession'] = people_data['primary_profession'].fillna('')
                
                # Additional data validation
                people_data = people_data[
                    (people_data['imdb_id'].notna()) &  # Ensure imdb_id is not null
                    (people_data['name'].str.len() > 0)  # Ensure name is not empty
                ]
                
                # Select only the columns we need in the correct order
                columns = ['imdb_id', 'name', 'birth_year', 'death_year', 'primary_profession']
                people_data = people_data[columns]
                
                print(f"Importing {len(people_data)} people records...")
                people_data.to_sql('people', conn, if_exists='append', index=False)
                
                logging.info(f"Imported {len(people_data)} people entries")
                print("✅ People import completed successfully!")
                
        except Exception as e:
            error_msg = f"Error importing people: {str(e)}"
            logging.error(error_msg)
            print(f"❌ {error_msg}")
            raise
        finally:
            if conn:
                conn.close()
                

    def import_ratings(self):
        """Import ratings data from title.ratings.tsv.gz"""
        try:
            logging.info("Starting ratings import")
            print("\nReading ratings data...")
            conn = self.connect_db()
            
            with gzip.open(self.data_dir / 'title.ratings.tsv.gz', 'rt', encoding='utf-8') as f:
                df = pd.read_csv(f, sep='\t')
                
                print("Processing ratings data...")
                ratings_data = df.rename(columns={
                    'tconst': 'media_id',
                    'averageRating': 'average_rating',
                    'numVotes': 'num_votes'
                })
                
                # Get the media_id to imdb_id mapping from the media table
                cursor = conn.cursor()
                cursor.execute("SELECT id, imdb_id FROM media")
                media_mapping = {row[1]: row[0] for row in cursor.fetchall()}
                
                # Map IMDb IDs to our media table IDs
                ratings_data['media_id'] = ratings_data['media_id'].map(media_mapping)
                
                # Remove rows where we couldn't map the media_id
                ratings_data = ratings_data.dropna(subset=['media_id'])
                
                print(f"Importing {len(ratings_data)} ratings records...")
                ratings_data.to_sql('ratings', conn, if_exists='append', index=False)
                
                logging.info(f"Imported {len(ratings_data)} ratings entries")
                print("✅ Ratings import completed successfully!")
            
        except Exception as e:
            error_msg = f"Error importing ratings: {str(e)}"
            logging.error(error_msg)
            print(f"❌ {error_msg}")
            raise
        finally:
            if conn:
                conn.close()
                

    def import_media_people(self):
        """Import cast and crew data"""
        try:
            logging.info("Starting media_people import")
            print("\nReading media_people data...")
            conn = self.connect_db()
            
            with gzip.open(self.data_dir / 'title.principals.tsv.gz', 'rt', encoding='utf-8') as f:
                df = pd.read_csv(f, sep='\t')
                
                print("Processing media_people data...")
                # Filter relevant categories
                df = df[df['category'].isin(['actor', 'actress', 'director', 'writer'])]
                
                media_people_data = df.rename(columns={
                    'tconst': 'media_id',
                    'nconst': 'person_id',
                    'category': 'role',
                    'characters': 'character_name'
                })
                
                # Combine actor/actress into just 'actor'
                media_people_data['role'] = media_people_data['role'].replace({
                    'actress': 'actor'
                })
                
                # Get ID mappings from database
                cursor = conn.cursor()
                cursor.execute("SELECT id, imdb_id FROM media")
                media_mapping = {row[1]: row[0] for row in cursor.fetchall()}
                
                cursor.execute("SELECT id, imdb_id FROM people")
                people_mapping = {row[1]: row[0] for row in cursor.fetchall()}
                
                # Map IMDb IDs to our database IDs
                media_people_data['media_id'] = media_people_data['media_id'].map(media_mapping)
                media_people_data['person_id'] = media_people_data['person_id'].map(people_mapping)
                
                # Remove rows where we couldn't map either ID
                media_people_data = media_people_data.dropna(subset=['media_id', 'person_id'])
                
                # Select only the columns we need
                columns = ['media_id', 'person_id', 'role', 'character_name']
                media_people_data = media_people_data[columns]
                
                print(f"Importing {len(media_people_data)} media_people records...")
                media_people_data.to_sql('media_people', conn, if_exists='append', index=False)
                
                logging.info(f"Imported {len(media_people_data)} media_people entries")
                print("✅ Media_people import completed successfully!")
                
        except Exception as e:
            error_msg = f"Error importing media_people: {str(e)}"
            logging.error(error_msg)
            print(f"❌ {error_msg}")
            raise
        finally:
            if conn:
                conn.close()


    def import_genres(self):
        """Import genres data from title.basics.tsv.gz"""
        try:
            logging.info("Starting genres import")
            print("\nReading genres data...")
            conn = self.connect_db()
            
            with gzip.open(self.data_dir / 'title.basics.tsv.gz', 'rt', encoding='utf-8') as f:
                df = pd.read_csv(f, sep='\t', low_memory=False)
                
                print("Processing genres data...")
                # Extract unique genres
                genres = set()
                for genre_list in df['genres'].dropna():
                    if genre_list != '\\N':  # IMDb's null value
                        genres.update(genre_list.split(','))
                
                # Convert to DataFrame
                genres_data = pd.DataFrame({'name': sorted(list(genres))})
                
                print(f"Importing {len(genres_data)} unique genres...")
                genres_data.to_sql('genres', conn, if_exists='append', index=False)
                
                logging.info(f"Imported {len(genres_data)} genres")
                print("✅ Genres import completed successfully!")      
        except Exception as e:
            error_msg = f"Error importing genres: {str(e)}"
            logging.error(error_msg)
            print(f"❌ {error_msg}")
            raise
        finally:
            if conn:
                conn.close()
                

    def import_media_genres(self):
        """Import media-genre relationships"""
        try:
            logging.info("Starting media_genres import")
            print("\nReading media_genres data...")
            conn = self.connect_db()
            
            with gzip.open(self.data_dir / 'title.basics.tsv.gz', 'rt', encoding='utf-8') as f:
                df = pd.read_csv(f, sep='\t', low_memory=False)
                
                print("Processing media_genres relationships...")
                # Get mappings
                cursor = conn.cursor()
                cursor.execute("SELECT id, imdb_id FROM media")
                media_mapping = {row[1]: row[0] for row in cursor.fetchall()}
                
                cursor.execute("SELECT id, name FROM genres")
                genre_mapping = {row[1]: row[0] for row in cursor.fetchall()}
                
                # Create relationships
                relationships = []
                for _, row in df.iterrows():
                    if pd.notna(row['genres']) and row['genres'] != '\\N':
                        media_id = media_mapping.get(row['tconst'])
                        if media_id:
                            for genre in row['genres'].split(','):
                                genre_id = genre_mapping.get(genre)
                                if genre_id:
                                    relationships.append({
                                        'media_id': media_id,
                                        'genre_id': genre_id
                                    })
                
                media_genres_data = pd.DataFrame(relationships)
                
                print(f"Importing {len(media_genres_data)} media-genre relationships...")
                media_genres_data.to_sql('media_genres', conn, if_exists='append', index=False)
                
                logging.info(f"Imported {len(media_genres_data)} media_genres entries")
                print("✅ Media_genres import completed successfully!")
                
        except Exception as e:
            error_msg = f"Error importing media_genres: {str(e)}"
            logging.error(error_msg)
            print(f"❌ {error_msg}")
            raise
        finally:
            if conn:
                conn.close()
                

def main():
    try:
        print("\n=== Starting IMDb Data Import Process ===")
        importer = IMDbDataImporter()
        
        print("\nStep 1/7: Initializing...")
        
        print("\nStep 2/7: Clearing existing data...")
        importer.clear_tables()
        
        print("\nStep 3/7: Importing media data...")
        importer.import_media()
        
        print("\nStep 4/7: Importing people data...")
        importer.import_people()
        
        print("\nStep 5/7: Importing genres data...")
        importer.import_genres()
        
        print("\nStep 6/7: Importing relationships...")
        print("- Importing ratings...")
        importer.import_ratings()
        print("- Importing media-people relationships...")
        importer.import_media_people()
        
        print("\nStep 7/7: Importing media-genre relationships...")
        importer.import_media_genres()
        
        logging.info("Data import completed successfully")
        print("\n✅ All data imported successfully!")
        print("Check the log file for detailed information.")
        
    except Exception as e:
        logging.error(f"Import process failed: {str(e)}")
        print(f"\n❌ Import process failed: {str(e)}")
        raise
    finally:
        print("\nPress Enter to exit...")
        input()
        

if __name__ == "__main__":
    main()
    