import sqlite3
from collections import defaultdict
import math

class MovieRecommender:
    def __init__(self, db_path):
        self.db_path = db_path
        
    def get_db_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def get_recommendations(self, user_id, limit=50):
        conn = self.db_connection()
        try:
            # Get user settings
            settings = conn.execute('''
                SELECT min_rating, year_from, year_to, 
                       include_watch_history, include_ratings, include_favorites
                FROM user_settings 
                WHERE user_id = ?
            ''', [user_id]).fetchone()
            
            if not settings:
                return []

            # Get user genre preferences
            genre_preferences = conn.execute('''
                SELECT genre_id, weight 
                FROM user_preferences 
                WHERE user_id = ?
            ''', [user_id]).fetchall()
            
            genre_weights = {row['genre_id']: row['weight'] for row in genre_preferences}
            
            # Base query to get eligible movies
            base_query = '''
                SELECT DISTINCT m.*, r.average_rating, GROUP_CONCAT(mg.genre_id) as genre_ids
                FROM media m
                JOIN media_genres mg ON m.id = mg.media_id
                JOIN ratings r ON m.id = r.media_id
                WHERE r.average_rating >= ?
                AND m.year BETWEEN ? AND ?
                AND m.id NOT IN (
                    SELECT media_id FROM watch_history WHERE user_id = ?
                )
                GROUP BY m.id
                HAVING MAX(CASE WHEN mg.genre_id IN ({}) THEN 1 ELSE 0 END) = 1
            '''.format(','.join('?' * len(genre_weights)))
            
            params = [
                settings['min_rating'],
                settings['year_from'],
                settings['year_to'],
                user_id
            ] + list(genre_weights.keys())

            movies = conn.execute(base_query, params).fetchall()
            
            # Calculate scores for each movie
            scored_movies = []
            for movie in movies:
                score = self.calculate_movie_score(
                    conn,
                    movie,
                    user_id,
                    genre_weights,
                    settings['include_watch_history'],
                    settings['include_favorites']
                )
                
                if score > 0:
                    scored_movies.append({
                        'movie': dict(movie),
                        'score': score
                    })

            # Sort by score and limit results
            scored_movies.sort(key=lambda x: x['score'], reverse=True)
            recommendations = scored_movies[:limit]

            # Store recommendations
            self.store_recommendations(conn, user_id, recommendations)

            return recommendations

        finally:
            conn.close()

    def calculate_movie_score(self, conn, movie, user_id, genre_weights, use_history, use_favorites):
        score = 0
        movie_genres = set(map(int, movie['genre_ids'].split(',')))
        
        # Base score from genre preferences
        for genre_id in movie_genres:
            if genre_id in genre_weights:
                score += genre_weights[genre_id]

        # Normalize genre score
        if len(movie_genres) > 0:
            score = score / len(movie_genres)

        # Rating contribution (0-1 scale)
        rating_score = (movie['average_rating'] - 5) / 5  # Normalize 5-10 rating to 0-1
        score += rating_score

        if use_history:
            history_score = self.calculate_history_similarity(conn, user_id, movie_genres)
            score += history_score * 0.5  # Weight history less than direct preferences

        if use_favorites:
            favorites_score = self.calculate_favorites_similarity(conn, user_id, movie_genres)
            score += favorites_score  # Weight favorites more heavily

        return score

    def calculate_history_similarity(self, conn, user_id, movie_genres):
        # Get genres from user's watch history
        history_genres = conn.execute('''
            SELECT DISTINCT mg.genre_id
            FROM watch_history wh
            JOIN media_genres mg ON wh.media_id = mg.media_id
            WHERE wh.user_id = ?
        ''', [user_id]).fetchall()
        
        history_genres = set(row['genre_id'] for row in history_genres)
        
        if not history_genres:
            return 0
            
        # Calculate Jaccard similarity
        intersection = len(movie_genres & history_genres)
        union = len(movie_genres | history_genres)
        
        return intersection / union if union > 0 else 0

    def calculate_favorites_similarity(self, conn, user_id, movie_genres):
        # Get genres from user's favorites
        favorites_genres = conn.execute('''
            SELECT DISTINCT mg.genre_id
            FROM favorites f
            JOIN media_genres mg ON f.item_id = mg.media_id
            WHERE f.user_id = ? AND f.item_type = 'media'
        ''', [user_id]).fetchall()
        
        favorites_genres = set(row['genre_id'] for row in favorites_genres)
        
        if not favorites_genres:
            return 0
            
        # Calculate Jaccard similarity with higher weight
        intersection = len(movie_genres & favorites_genres)
        union = len(movie_genres | favorites_genres)
        
        return 1.5 * (intersection / union) if union > 0 else 0

    def store_recommendations(self, conn, user_id, recommendations):
        # Clear old recommendations
        conn.execute('DELETE FROM user_recommendations WHERE user_id = ?', [user_id])
        
        # Store new recommendations
        for rank, rec in enumerate(recommendations, 1):
            conn.execute('''
                INSERT INTO user_recommendations (user_id, media_id, score, rank)
                VALUES (?, ?, ?, ?)
            ''', [user_id, rec['movie']['id'], rec['score'], rank])
        
        conn.commit()

    def get_stored_recommendations(self, user_id, limit=None):
        """Retrieve stored recommendations for a user"""
        conn = self.get_db_connection()
        try:
            query = '''
                SELECT m.*, r.score, r.rank
                FROM user_recommendations r
                JOIN media m ON r.media_id = m.id
                WHERE r.user_id = ?
                ORDER BY r.rank
            '''
            
            if limit:
                query += ' LIMIT ?'
                params = [user_id, limit]
            else:
                params = [user_id]
                
            return conn.execute(query, params).fetchall()
        finally:
            conn.close()

    def refresh_recommendations(self, user_id):
        """Force refresh of user recommendations"""
        self.get_recommendations(user_id)