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
recommender = MovieRecommender('D:\Programming\What To Watch\wtwData\movies.db')

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
            
            # Save favorite movies
            for movie_id in request.form.getlist('favorite_movies[]'):
                conn.execute('''
                    INSERT INTO favorites (user_id, item_id, item_type)
                    VALUES (?, ?, 'movie')
                ''', [current_user.id, movie_id])
            
            # Save favorite people (actors/directors)
            for person_id in request.form.getlist('favorite_people[]'):
                conn.execute('''
                    INSERT INTO favorites (user_id, item_id, item_type)
                    VALUES (?, ?, 'person')
                ''', [current_user.id, person_id])
            
            # Save general preferences
            min_rating = request.form.get('min_rating', 6.0)
            year_from = request.form.get('year_from', 1900)
            year_to = request.form.get('year_to', 2024)
            
            conn.execute('''
                INSERT OR REPLACE INTO user_settings 
                (user_id, min_rating, year_from, year_to)
                VALUES (?, ?, ?, ?)
            ''', [current_user.id, min_rating, year_from, year_to])
            
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
        
        # Get user's favorites
        # Get user's favorites
        favorites = conn.execute('''
            SELECT f.*, 
                   CASE 
                       WHEN f.item_type = 'movie' THEN m.title
                       WHEN f.item_type = 'person' THEN p.name
                   END as item_name,
                   CASE 
                       WHEN f.item_type = 'person' THEN mp.role
                   END as person_role
            FROM favorites f
            LEFT JOIN media m ON f.item_id = m.id AND f.item_type = 'movie'
            LEFT JOIN people p ON f.item_id = p.id AND f.item_type = 'person'
            LEFT JOIN media_people mp ON p.id = mp.person_id
            WHERE f.user_id = ?
            GROUP BY f.id
        ''', [current_user.id]).fetchall()
        
        # Get user settings
        settings = conn.execute('''
            SELECT * FROM user_settings WHERE user_id = ?
        ''', [current_user.id]).fetchone()
        
        if not settings:
            settings = {
                'min_rating': 6.0,
                'year_from': 1900,
                'year_to': 2024
            }
        
        # Format favorites by type
        favorite_movies = [f for f in favorites if f['item_type'] == 'movie']
        favorite_people = [f for f in favorites if f['item_type'] == 'person']
        
        return render_template(
            'preferences.html',
            genres=genres,
            user_preferences=dict((p['genre_id'], p['weight']) for p in user_prefs),
            favorite_movies=favorite_movies,
            favorite_people=favorite_people,
            settings=settings
        )
        
    finally:
        conn.close()
        

@app.route("/api/search/movies")
@login_required
def search_movies():
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify([])
    
    conn = get_db_connection()
    try:
        # Modified query to match your schema where type is either 'movie' or 'tv'
        media = conn.execute('''
            SELECT 
                m.id, 
                m.title, 
                m.year, 
                m.type,
                m.poster_url,
                COALESCE(r.average_rating, 0) as rating
            FROM media m
            LEFT JOIN ratings r ON m.id = r.media_id
            WHERE LOWER(m.title) LIKE LOWER(?)
            AND m.type IN ('movie', 'tv')
            ORDER BY 
                CASE WHEN r.average_rating IS NULL THEN 1 ELSE 0 END,
                r.average_rating DESC,
                m.year DESC
            LIMIT 10
        ''', [f'%{query}%']).fetchall()
        
        return jsonify([{
            'id': m['id'],
            'title': m['title'],
            'year': m['year'],
            'type': m['type'],
            'rating': m['rating'],
            'poster_url': m['poster_url']
        } for m in media])
    finally:
        conn.close()

@app.route("/api/search/people")
@login_required
def search_people():
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify([])
    
    conn = get_db_connection()
    try:
        # Modified query to remove popularity sorting
        people = conn.execute('''
            SELECT DISTINCT p.id, p.name, 
                   GROUP_CONCAT(DISTINCT mp.role) as roles,
                   COUNT(DISTINCT m.id) as movie_count
            FROM people p
            JOIN media_people mp ON p.id = mp.person_id
            JOIN media m ON mp.media_id = m.id
            WHERE LOWER(p.name) LIKE LOWER(?)
            AND mp.role IN ('actor', 'director')
            GROUP BY p.id
            ORDER BY movie_count DESC  -- Sort by number of movies instead of popularity
            LIMIT 10
        ''', [f'%{query}%']).fetchall()
        
        # Format the results
        results = []
        for person in people:
            roles = list(set(person['roles'].split(','))) if person['roles'] else []
            results.append({
                'id': person['id'],
                'name': person['name'],
                'roles': roles,
                'movie_count': person['movie_count']
            })
        
        return jsonify(results)
    finally:
        conn.close()

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