from datetime import datetime
import sqlite3
from collections import defaultdict

class MovieRecommender:
    def __init__(self, db_path):
        self.db_path = db_path
        
    def get_db_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def get_user_profile(self, user_id):
        """Get comprehensive user profile including preferences, history, and favorites"""
        conn = self.get_db_connection()
        try:
            # Get genre preferences with weights
            genre_preferences = conn.execute("""
                SELECT g.id, g.name, COALESCE(up.weight, 1.0) as weight
                FROM genres g
                LEFT JOIN user_preferences up ON g.id = up.genre_id AND up.user_id = ?
            """, [user_id]).fetchall()
            
            # Get watch history with ratings
            watch_history = conn.execute("""
                SELECT m.id, m.title, wh.rating, m.year,
                       GROUP_CONCAT(DISTINCT g.id) as genre_ids
                FROM watch_history wh
                JOIN media m ON wh.media_id = m.id
                LEFT JOIN media_genres mg ON m.id = mg.media_id
                LEFT JOIN genres g ON mg.genre_id = g.id
                WHERE wh.user_id = ?
                GROUP BY m.id
                ORDER BY wh.watch_date DESC
            """, [user_id]).fetchall()
            
            # Get favorite people and genres
            favorites = conn.execute("""
                SELECT f.item_id, f.item_type, 
                       CASE 
                           WHEN f.item_type = 'person' THEN p.name 
                           WHEN f.item_type = 'genre' THEN g.name 
                       END as name,
                       mp.role
                FROM favorites f
                LEFT JOIN people p ON f.item_id = p.id AND f.item_type = 'person'
                LEFT JOIN genres g ON f.item_id = g.id AND f.item_type = 'genre'
                LEFT JOIN media_people mp ON p.id = mp.person_id
                WHERE f.user_id = ?
            """, [user_id]).fetchall()
            
            # Process favorites into separate categories
            favorite_people = []
            favorite_genres = []
            for fav in favorites:
                if fav['item_type'] == 'person':
                    favorite_people.append({'id': fav['item_id'], 'name': fav['name'], 'role': fav['role']})
                elif fav['item_type'] == 'genre':
                    favorite_genres.append({'id': fav['item_id'], 'name': fav['name']})
            
            return {
                'genre_preferences': [dict(g) for g in genre_preferences],
                'watch_history': [dict(w) for w in watch_history],
                'favorite_people': favorite_people,
                'favorite_genres': favorite_genres
            }
            
        finally:
            conn.close()

    def calculate_scores(self, movie, user_profile):
        """Calculate all recommendation scores for a movie"""
        # Genre score
        genre_weights = {g['id']: float(g['weight']) for g in user_profile['genre_preferences']}
        favorite_genres = {g['id'] for g in user_profile['favorite_genres']}
        
        genre_score = 0.5
        if movie['genres']:
            total_weight = matched_weight = 0
            for genre in movie['genres']:
                weight = genre_weights.get(genre['id'], 1.0)
                if genre['id'] in favorite_genres:
                    weight *= 1.5
                total_weight += weight
                matched_weight += weight
            genre_score = matched_weight / total_weight if total_weight > 0 else 0.5

        # People score
        people_score = 0.5
        if movie['people'] and user_profile['favorite_people']:
            favorite_people = {(p['id'], p['role']): p for p in user_profile['favorite_people']}
            matches = sum(1 for p in movie['people'] if (p['id'], p['role']) in favorite_people)
            people_score = min(1.0, matches * 0.25)

        # Similarity score
        similarity_score = 0.5
        if user_profile['watch_history']:
            similar_ratings = []
            for watched in user_profile['watch_history']:
                watched_genres = set(map(int, watched['genre_ids'].split(','))) if watched['genre_ids'] else set()
                movie_genres = set(g['id'] for g in movie['genres'])
                
                genre_overlap = len(watched_genres & movie_genres) / len(watched_genres | movie_genres) if watched_genres and movie_genres else 0
                
                if genre_overlap > 0.3:
                    similar_ratings.append((watched['rating'], genre_overlap))
            
            if similar_ratings:
                weighted_rating = sum(rating * overlap for rating, overlap in similar_ratings)
                total_weight = sum(overlap for _, overlap in similar_ratings)
                similarity_score = min(1.0, (weighted_rating / total_weight) / 10.0)

        # Calculate final score
        rating_score = float(movie.get('average_rating', 5.0)) / 10.0
        
        return {
            'genre_score': genre_score,
            'people_score': people_score,
            'similarity_score': similarity_score,
            'rating_score': rating_score,
            'final_score': (
                genre_score * 0.35 +
                people_score * 0.25 +
                similarity_score * 0.25 +
                rating_score * 0.15
            )
        }

    def store_recommendations(self, user_id, recommendations):
        """Store user recommendations in the database"""
        conn = self.get_db_connection()
        try:
            conn.execute('BEGIN TRANSACTION')
            conn.execute('DELETE FROM user_recommendations WHERE user_id = ?', [user_id])
            
            for rank, rec in enumerate(recommendations, 1):
                conn.execute('''
                    INSERT INTO user_recommendations 
                    (user_id, media_id, score, rank, generated_at)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (user_id, rec['movie']['id'], rec['score'], rank))
            
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()

    def get_stored_recommendations(self, user_id, limit=None):
        """Get stored recommendations for a user"""
        conn = self.get_db_connection()
        try:
            query = '''
                SELECT m.*, r.average_rating, r.num_votes,
                       COALESCE(m.poster_url, '/static/images/no-poster.jpg') as poster_url,
                       ur.score as recommendation_score,
                       ur.rank as recommendation_rank,
                       ur.generated_at,
                       GROUP_CONCAT(DISTINCT g.id || ',' || g.name) as genre_data,
                       GROUP_CONCAT(DISTINCT mp.person_id || ',' || mp.role || ',' || p.name) as people_data
                FROM user_recommendations ur
                JOIN media m ON ur.media_id = m.id
                LEFT JOIN ratings r ON m.id = r.media_id
                LEFT JOIN media_genres mg ON m.id = mg.media_id
                LEFT JOIN genres g ON mg.genre_id = g.id
                LEFT JOIN media_people mp ON m.id = mp.media_id
                LEFT JOIN people p ON mp.person_id = p.id
                WHERE ur.user_id = ?
                GROUP BY m.id
                ORDER BY ur.rank
            '''
            if limit:
                query += ' LIMIT ?'
                params = [user_id, limit]
            else:
                params = [user_id]
                
            return [dict(row) for row in conn.execute(query, params).fetchall()]
        finally:
            conn.close()

    def needs_refresh(self, user_id, max_age_hours=24):
        """Check if recommendations need to be refreshed"""
        conn = self.get_db_connection()
        try:
            result = conn.execute('''
                SELECT generated_at 
                FROM user_recommendations 
                WHERE user_id = ? 
                ORDER BY generated_at DESC 
                LIMIT 1
            ''', [user_id]).fetchone()
            
            if not result:
                return True
                
            generated_at = datetime.strptime(result['generated_at'], '%Y-%m-%d %H:%M:%S')
            age = datetime.utcnow() - generated_at
            return age.total_seconds() / 3600 > max_age_hours
        finally:
            conn.close()

    def generate_recommendations(self, user_id, limit=20):
        """Generate new recommendations for a user"""
        user_profile = self.get_user_profile(user_id)
        conn = self.get_db_connection()
        try:
            movies = conn.execute("""
                SELECT m.*, r.average_rating, r.num_votes,
                    COALESCE(m.poster_url, '/static/images/no-poster.jpg') as poster_url,
                    GROUP_CONCAT(DISTINCT g.id || ',' || g.name) as genre_data,
                    GROUP_CONCAT(DISTINCT mp.person_id || ',' || mp.role || ',' || p.name) as people_data
                FROM media m
                LEFT JOIN media_genres mg ON m.id = mg.media_id
                LEFT JOIN genres g ON mg.genre_id = g.id
                LEFT JOIN ratings r ON m.id = r.media_id
                LEFT JOIN media_people mp ON m.id = mp.media_id
                LEFT JOIN people p ON mp.person_id = p.id
                WHERE m.id NOT IN (
                    SELECT media_id FROM watch_history WHERE user_id = ?
                )
                AND m.type = 'movie'
                GROUP BY m.id
                HAVING r.average_rating >= 6.0
            """, [user_id]).fetchall()
            
            scored_movies = []
            for movie in movies:
                movie = dict(movie)
                self._parse_movie_data(movie)
                scores = self.calculate_scores(movie, user_profile)
                
                scored_movies.append({
                    'movie': movie,
                    'score': scores['final_score'],
                    'score_components': scores
                })
            
            scored_movies.sort(key=lambda x: x['score'], reverse=True)
            return scored_movies[:limit]
            
        finally:
            conn.close()

    def _parse_movie_data(self, movie):
        """Parse genre and people data from database format"""
        # Parse genres
        movie['genres'] = []
        if movie['genre_data']:
            for genre_str in movie['genre_data'].split(','):
                if ',' in genre_str:
                    gid, gname = genre_str.split(',')
                    movie['genres'].append({'id': int(gid), 'name': gname})
        
        # Parse people
        movie['people'] = []
        if movie['people_data']:
            for person_str in movie['people_data'].split(','):
                if len(person_str.split(',')) == 3:
                    pid, role, name = person_str.split(',')
                    movie['people'].append({
                        'id': int(pid),
                        'role': role,
                        'name': name
                    })
        
        # Organize cast and crew
        movie['cast'] = [p['name'] for p in movie['people'] if p['role'] == 'actor'][:5]  # Top 5 actors
        movie['director'] = next((p['name'] for p in movie['people'] if p['role'] == 'director'), 'Unknown')
        
        # Format rating and release date
        movie['rating'] = float(movie['average_rating']) if movie['average_rating'] else None
        movie['release_date'] = str(movie['year']) if movie['year'] else 'Unknown'
        
        # Create a brief overview if available
        movie['overview'] = movie.get('plot', '')[:200] + '...' if movie.get('plot') else 'No overview available.'
        
        # Clean up temporary data fields
        fields_to_remove = ['genre_data', 'people_data', 'average_rating']
        for field in fields_to_remove:
            if field in movie:
                del movie[field]
        
        return movie
    
    def get_recommendations(self, user_id, limit=20, force_refresh=False):
        """Get recommendations for a user, either from cache or generate new ones"""
        # Force refresh if requested or check if cache needs refresh
        if force_refresh or self.needs_refresh(user_id):
            try:
                # Generate new recommendations
                recommendations = self.generate_recommendations(user_id, limit)
                # Store in cache
                self.store_recommendations(user_id, recommendations)
                return recommendations
            except Exception as e:
                print(f"Error generating recommendations: {e}")
                # Fallback to cached recommendations if available
                stored_recs = self.get_stored_recommendations(user_id, limit)
                if stored_recs:
                    return self._format_stored_recommendations(stored_recs)
                raise  # Re-raise the exception if no fallback available
        
        # Get recommendations from cache
        stored_recs = self.get_stored_recommendations(user_id, limit)
        if not stored_recs:
            # Generate new ones if cache is empty
            recommendations = self.generate_recommendations(user_id, limit)
            self.store_recommendations(user_id, recommendations)
            return recommendations
            
        return self._format_stored_recommendations(stored_recs)

    def _format_stored_recommendations(self, stored_recs):
        """Format stored recommendations to match the expected structure"""
        formatted_recs = []
        for movie in stored_recs:
            # Parse the movie data
            parsed_movie = self._parse_movie_data(dict(movie))
            
            formatted_recs.append({
                'movie': parsed_movie,
                'score': movie['recommendation_score'],
                'score_components': {
                    'final_score': movie['recommendation_score'],
                    # Reconstruct approximate component scores based on final score
                    'genre_score': movie['recommendation_score'] * 0.35,
                    'people_score': movie['recommendation_score'] * 0.25,
                    'similarity_score': movie['recommendation_score'] * 0.25,
                    'rating_score': float(movie.get('average_rating', 5.0)) / 10.0
                }
            })
        
        return formatted_recs