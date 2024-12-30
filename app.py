from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
import math
from sqlite3 import Error

from recommendations import MovieRecommender

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'  # Change this to a secure secret key

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Database helper functions
DB_PATH = r"D:\Programming\What To Watch\wtwData\movies.db"

# Initialize the recommender
recommender = MovieRecommender(DB_PATH)

def get_db_connection():
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    except Error as e:
        print(e)
        return None

def query_db(query, args=(), one=False):
    conn = get_db_connection()
    if not conn:
        return None
    cur = conn.cursor()
    try:
        cur.execute(query, args)
        rv = cur.fetchall()
        conn.commit()
        return (rv[0] if rv else None) if one else rv
    except Error as e:
        print(e)
        return None
    finally:
        cur.close()
        conn.close()

# User class for Flask-Login
class User(UserMixin):
    def __init__(self, id, username):
        self.id = id
        self.username = username

@login_manager.user_loader
def load_user(user_id):
    user = query_db('SELECT * FROM users WHERE id = ?', [user_id], one=True)
    if not user:
        return None
    return User(user['id'], user['username'])

@app.route("/")
def index():
    if current_user.is_authenticated:
        # Get stored recommendations for homepage
        recommendations = recommender.get_stored_recommendations(current_user.id, limit=6)
        return render_template("index.html", recommended_movies=recommendations)
    return render_template("index.html", recommended_movies=[])

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if not username:
            flash("Must provide username", "login-error")
            return render_template("login.html")
        elif not password:
            flash("Must provide password", "login-error")
            return render_template("login.html")

        user = query_db('SELECT * FROM users WHERE username = ?', [username], one=True)

        if not user or not check_password_hash(user['hash'], password):
            flash("Invalid username and/or password", "login-error")
            return render_template("login.html")

        user_obj = User(user['id'], user['username'])
        login_user(user_obj)
        flash("Successfully logged in!", "login-success")
        return redirect(url_for('index'))

    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Successfully logged out!", "success")
    return redirect(url_for('index'))

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        if not username:
            flash("Must provide username", "register-error")
            return render_template("register.html")
        elif not password:
            flash("Must provide password", "register-error")
            return render_template("register.html")
        elif not confirmation:
            flash("Must provide password confirmation", "register-error")
            return render_template("register.html")
        elif password != confirmation:
            flash("Passwords must match", "register-error")
            return render_template("register.html")

        existing_user = query_db('SELECT id FROM users WHERE username = ?', [username], one=True)
        if existing_user:
            flash("Username already exists", "register-error")
            return render_template("register.html")

        hash = generate_password_hash(password)
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute('INSERT INTO users (username, hash) VALUES (?, ?)', (username, hash))
            new_user_id = cur.lastrowid
            conn.commit()
            conn.close()

            user = User(new_user_id, username)
            login_user(user)
            flash("Registration successful! Welcome!", "register-success")
            return redirect(url_for('index'))
        except Error as e:
            print(e)
            flash("Registration failed", "register-error")
            return render_template("register.html")

    return render_template("register.html")

@app.route("/api/watch-history", methods=['DELETE'])
@login_required
def remove_from_history():
    try:
        data = request.json
        media_id = data['media_id']
        
        conn = get_db_connection()
        conn.execute('''
            DELETE FROM watch_history
            WHERE user_id = ? AND media_id = ?
        ''', [current_user.id, media_id])
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route("/preferences", methods=['GET', 'POST'])
@login_required
def preferences():
    conn = get_db_connection()
    
    if request.method == 'POST':
        try:
            # Begin transaction
            conn.execute('BEGIN TRANSACTION')
            
            # Clear existing preferences
            conn.execute('DELETE FROM user_preferences WHERE user_id = ?', [current_user.id])
            conn.execute('DELETE FROM favorites WHERE user_id = ?', [current_user.id])
            
            # Save genre preferences
            for genre_id in request.form.getlist('genres[]'):
                weight = request.form.get(f'genre_weight_{genre_id}', 1.0)
                conn.execute('''
                    INSERT INTO user_preferences (user_id, genre_id, weight)
                    VALUES (?, ?, ?)
                ''', [current_user.id, genre_id, weight])
            
            # Save general preferences
            min_rating = request.form.get('min_rating', 6.0)
            year_from = request.form.get('year_from', 1900)
            year_to = request.form.get('year_to', 2024)
            
            conn.execute('''
                INSERT OR REPLACE INTO user_settings 
                (user_id, min_rating, year_from, year_to, include_watch_history, include_ratings, include_favorites)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', [
                current_user.id, 
                min_rating, 
                year_from, 
                year_to, 
                request.form.get('include_watch_history') == 'on', 
                request.form.get('include_ratings') == 'on', 
                request.form.get('include_favorites') == 'on'
            ])
            
            conn.commit()
            flash('Preferences saved successfully!', 'success')
            
        except Exception as e:
            conn.rollback()
            flash('Error saving preferences: ' + str(e), 'error')
        finally:
            conn.close()
        
        return redirect(url_for('preferences'))
    
    # GET request - show preferences form
    try:
        # Get all genres
        genres = conn.execute('SELECT * FROM genres ORDER BY name').fetchall()
        
        # Get user's current preferences
        user_prefs = conn.execute('''
            SELECT genre_id, weight 
            FROM user_preferences 
            WHERE user_id = ?
        ''', [current_user.id]).fetchall()
        
        # Get user settings
        settings = conn.execute('''
            SELECT * FROM user_settings WHERE user_id = ?
        ''', [current_user.id]).fetchone()
        
        if not settings:
            settings = {
                'min_rating': 6.0,
                'year_from': 1900,
                'year_to': 2024,
                'include_watch_history': True,
                'include_ratings': True,
                'include_favorites': True
            }
        
        return render_template(
            'preferences.html',
            genres=genres,
            user_preferences=dict((p['genre_id'], p['weight']) for p in user_prefs),
            settings=settings
        )
        
    finally:
        conn.close()

@app.route("/search")
@login_required
def search():
    return render_template("search.html")

@app.route("/api/suggestions")
@login_required
def api_suggestions():
    query = request.args.get('query', '').strip()
    search_type = request.args.get('type', 'movie')
    
    if not query:
        return jsonify([])

    conn = get_db_connection()
    try:
        # Using LIKE with query% to match from the start of titles
        results = conn.execute('''
            SELECT title, year 
            FROM media 
            WHERE type = ? AND LOWER(title) LIKE LOWER(?) 
            ORDER BY 
                CASE 
                    WHEN LOWER(title) = LOWER(?) THEN 1  -- Exact match
                    WHEN LOWER(title) LIKE LOWER(?) THEN 2  -- Starts with
                    ELSE 3
                END,
                title
            LIMIT 10
        ''', (search_type, f'{query}%', query, f'{query}%')).fetchall()
        
        suggestions = [
            {
                'label': f"{row['title']} ({row['year']})",
                'value': row['title']
            }
            for row in results
        ]
        return jsonify(suggestions)
    finally:
        conn.close()

@app.route("/api/search_query")
@login_required
def api_search():
    query = request.args.get('query', '').strip()
    search_type = request.args.get('type', 'movie')
    
    if not query:
        return jsonify([])

    # Split query into words for whole word matching
    search_words = query.lower().split()

    conn = get_db_connection()
    try:
        # Create a WHERE clause that matches whole words
        where_clauses = []
        params = [search_type]
        
        for word in search_words:
            where_clauses.append("""
                (
                    LOWER(title) LIKE ? OR
                    LOWER(title) LIKE ? OR
                    LOWER(title) LIKE ? OR
                    LOWER(title) LIKE ?
                )
            """)
            # Match word at start, end, or between spaces
            params.extend([
                f'{word}%',          # Starts with word
                f'% {word}%',        # Has word between spaces
                f'% {word}',         # Ends with word
                f'{word}'            # Exact match
            ])
        
        query_sql = f"""
            SELECT m.*, COALESCE(r.average_rating, 0) as average_rating
            FROM media m
            LEFT JOIN ratings r ON m.id = r.media_id
            WHERE m.type = ? AND {' AND '.join(where_clauses)}
            ORDER BY 
                CASE 
                    WHEN LOWER(title) = LOWER(?) THEN 1
                    ELSE 2
                END,
                title
            LIMIT 20
        """
        params.append(query)  # Add original query for exact match sorting
        
        results = conn.execute(query_sql, params).fetchall()
        return jsonify([dict(row) for row in results])
    finally:
        conn.close()


@app.route("/api/save-genre-preference", methods=['POST'])
@login_required
def save_genre_preference():
    try:
        data = request.json
        genre_id = data['genre_id']
        weight = data['weight']
        checked = data['checked']
        
        conn = get_db_connection()
        try:
            if checked:
                conn.execute('''
                    INSERT OR REPLACE INTO user_preferences 
                    (user_id, genre_id, weight, updated_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ''', [current_user.id, genre_id, weight])
            else:
                conn.execute('''
                    DELETE FROM user_preferences
                    WHERE user_id = ? AND genre_id = ?
                ''', [current_user.id, genre_id])
            
            conn.commit()
            return jsonify({'success': True})
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
            
    except Exception as e:
        return jsonify({'error': str(e)}), 400
    
@app.route("/api/save-settings", methods=['POST'])
@login_required
def save_settings():
    try:
        data = request.json
        min_rating = float(data.get('min_rating', 6.0))
        year_from = int(data.get('year_from', 1900))
        year_to = int(data.get('year_to', 2024))
        include_watch_history = data.get('include_watch_history', True)
        include_ratings = data.get('include_ratings', True)
        include_favorites = data.get('include_favorites', True)
        
        conn = get_db_connection()
        try:
            conn.execute('''
                INSERT OR REPLACE INTO user_settings 
                (user_id, min_rating, year_from, year_to, include_watch_history, include_ratings, include_favorites, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', [current_user.id, min_rating, year_from, year_to, include_watch_history, include_ratings, include_favorites])
            
            conn.commit()
            return jsonify({'success': True})
        finally:
            conn.close()
            
    except Exception as e:
        return jsonify({'error': str(e)}), 400
    
@app.route("/api/update-rating", methods=['POST'])
@login_required
def update_rating():
    try:
        data = request.json
        media_id = data['media_id']
        rating = data['rating']
        
        conn = get_db_connection()
        conn.execute('''
            UPDATE watch_history
            SET rating = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ? AND media_id = ?
        ''', [rating, current_user.id, media_id])
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 400
    
@app.route("/recommendations")
@login_required
def recommendations():
    # Get query parameters
    page = request.args.get('page', 1, type=int)
    sort_by = request.args.get('sort', 'relevance')
    min_rating = request.args.get('rating', 6.0, type=float)
    year_from = request.args.get('yearFrom', 1900, type=int)
    year_to = request.args.get('yearTo', 2024, type=int)
    selected_genres = request.args.getlist('genres[]')
    selected_languages = request.args.getlist('languages[]')
    
    # Get recommendations
    recommendations = recommender.get_recommendations(current_user.id)
    
    # Apply filters
    filtered_movies = []
    for rec in recommendations:
        movie = rec['movie']
        # Add additional movie info
        movie['overview'] = movie.get('plot', '')  # Use plot field from your database
        movie['rating'] = movie.get('average_rating', 0)
        movie['release_date'] = str(movie.get('year', ''))
        
        # Get genres for the movie
        conn = get_db_connection()
        genres = conn.execute('''
            SELECT g.name 
            FROM media_genres mg 
            JOIN genres g ON mg.genre_id = g.id 
            WHERE mg.media_id = ?
        ''', [movie['id']]).fetchall()
        movie['genres'] = [g['name'] for g in genres]
        
        # Get cast and director
        people = conn.execute('''
            SELECT p.name, mp.role 
            FROM media_people mp 
            JOIN people p ON mp.person_id = p.id 
            WHERE mp.media_id = ? AND mp.role IN ('actor', 'director')
        ''', [movie['id']]).fetchall()
        
        movie['cast'] = [p['name'] for p in people if p['role'] == 'actor'][:5]  # Limit to 5 actors
        movie['director'] = next((p['name'] for p in people if p['role'] == 'director'), 'Unknown')
        
        conn.close()
        
        # Apply filters
        if (
            (not selected_genres or any(g in selected_genres for g in movie['genres'])) and
            movie.get('rating', 0) >= min_rating and
            year_from <= movie.get('year', 0) <= year_to
        ):
            filtered_movies.append(movie)
    
    # Sort movies
    if sort_by == 'rating':
        filtered_movies.sort(key=lambda x: x.get('rating', 0), reverse=True)
    elif sort_by == 'year':
        filtered_movies.sort(key=lambda x: x.get('year', 0), reverse=True)
    elif sort_by == 'title':
        filtered_movies.sort(key=lambda x: x.get('title', ''))
    # relevance is default (no sort needed as recommendations are already sorted)
    
    # Pagination
    items_per_page = 12
    total_items = len(filtered_movies)
    total_pages = math.ceil(total_items / items_per_page)
    start_idx = (page - 1) * items_per_page
    end_idx = start_idx + items_per_page
    current_page_movies = filtered_movies[start_idx:end_idx]
    
    # Get all available genres and languages for filters
    conn = get_db_connection()
    all_genres = [g['name'] for g in conn.execute('SELECT name FROM genres ORDER BY name').fetchall()]
    
    # For languages, you might want to add a languages table, for now using a static list
    all_languages = [
        {'code': 'en', 'name': 'English'},
        {'code': 'es', 'name': 'Spanish'},
        {'code': 'fr', 'name': 'French'},
        # Add more languages as needed
    ]
    conn.close()
    
    return render_template(
        "recommendations.html",
        movies=current_page_movies,
        page=page,
        total_pages=total_pages,
        sort_by=sort_by,
        min_rating=min_rating,
        year_from=year_from,
        year_to=year_to,
        selected_genres=all_genres,
        selected_languages=all_languages
    )

if __name__ == '__main__':
    app.run(debug=True)