from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
import math
from sqlite3 import Error
from datetime import datetime

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
        # Only handle movie/TV show search
        results = conn.execute('''
            SELECT title, year 
            FROM media 
            WHERE type = ? AND LOWER(title) LIKE LOWER(?) 
            ORDER BY 
                CASE 
                    WHEN LOWER(title) = LOWER(?) THEN 1
                    WHEN LOWER(title) LIKE LOWER(?) THEN 2
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
    sort_by = request.args.get('sort', 'relevance')
    
    if not query:
        return jsonify([])

    conn = get_db_connection()
    try:
        # Updated query to include favorite status
        query_sql = '''
            SELECT 
                m.*,
                r.average_rating,
                r.num_votes,
                GROUP_CONCAT(DISTINCT g.name) as genres,
                CASE WHEN f.id IS NOT NULL THEN 1 ELSE 0 END as is_favorite,
                CASE WHEN w.id IS NOT NULL THEN 1 ELSE 0 END as in_watchlist
            FROM media m
            LEFT JOIN ratings r ON m.id = r.media_id
            LEFT JOIN media_genres mg ON m.id = mg.media_id
            LEFT JOIN genres g ON mg.genre_id = g.id
            LEFT JOIN favorites f ON m.id = f.item_id 
                AND f.user_id = ? 
                AND f.item_type = 'media'
            LEFT JOIN watchlist w ON m.id = w.media_id 
                AND w.user_id = ?
            WHERE m.type = ? AND (
                LOWER(m.title) LIKE LOWER(?) OR
                LOWER(m.plot) LIKE LOWER(?) OR
                EXISTS (
                    SELECT 1 FROM media_genres mg2
                    JOIN genres g2 ON mg2.genre_id = g2.id
                    WHERE mg2.media_id = m.id AND LOWER(g2.name) LIKE LOWER(?)
                )
            )
            GROUP BY m.id
        '''
        
        # Base parameters including user_id for favorites and watchlist
        params = [current_user.id, current_user.id, search_type, f'%{query}%', f'%{query}%', f'%{query}%']

        # Add sorting
        if sort_by == 'rating':
            query_sql += ' ORDER BY r.average_rating DESC NULLS LAST, m.title'
        elif sort_by == 'year':
            query_sql += ' ORDER BY m.year DESC, m.title'
        elif sort_by == 'title':
            query_sql += ' ORDER BY m.title'
        else:  # relevance
            query_sql += '''
                ORDER BY 
                    CASE 
                        WHEN LOWER(m.title) = LOWER(?) THEN 1
                        WHEN LOWER(m.title) LIKE LOWER(?) THEN 2
                        WHEN LOWER(m.plot) LIKE LOWER(?) THEN 3
                        ELSE 4
                    END,
                    r.average_rating DESC NULLS LAST,
                    m.title
            '''
            params.extend([query, f'{query}%', f'%{query}%'])

        query_sql += ' LIMIT 20'
        
        results = conn.execute(query_sql, params).fetchall()
        
        processed_results = []
        for row in results:
            result_dict = {
                'id': row['id'],
                'title': row['title'],
                'year': row['year'],
                'type': row['type'],
                'plot': row['plot'],
                'average_rating': float(row['average_rating']) if row['average_rating'] else None,
                'num_votes': row['num_votes'],
                'genres': row['genres'].split(',') if row['genres'] else [],
                'poster_url': '/static/images/no-poster.png', 
                'is_favorite': bool(row['is_favorite']),  
                'in_watchlist': bool(row['in_watchlist']) 
            }
            processed_results.append(result_dict)

        return jsonify(processed_results)

    except Exception as e:
        print(f"Search error: {str(e)}")
        return jsonify({'error': 'An error occurred during search'}), 500
    finally:
        conn.close()
        
@app.route('/api/check-favorite/<int:media_id>')
@login_required
def check_favorite(media_id):
    is_favorite = db.session.query(Favorite).filter_by(
        user_id=current_user.id,
        item_id=media_id,
        item_type='media'
    ).first() is not None
    return jsonify({'is_favorite': is_favorite})

@app.template_filter('datetime')
def format_datetime(value):
    if value:
        if isinstance(value, str):
            try:
                dt = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                try:
                    dt = datetime.strptime(value, '%Y-%m-%d')
                except ValueError:
                    return value
        else:
            dt = value
        return dt.strftime('%Y-%m-%d %H:%M')
    return 'N/A'
 
@app.route("/api/favorites", methods=['POST', 'DELETE'])
@login_required
def manage_favorites():
    try:
        data = request.json
        item_id = data.get('item_id')
        item_type = data.get('item_type', 'media')  # 'media' or 'person'

        if not item_id:
            return jsonify({'error': 'Missing item_id'}), 400

        conn = get_db_connection()
        try:
            if request.method == 'POST':
                conn.execute('''
                    INSERT OR IGNORE INTO favorites 
                    (user_id, item_id, item_type, date_added)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ''', [current_user.id, item_id, item_type])
            else:  # DELETE
                conn.execute('''
                    DELETE FROM favorites
                    WHERE user_id = ? AND item_id = ? AND item_type = ?
                ''', [current_user.id, item_id, item_type])
            
            conn.commit()
            return jsonify({'success': True})
        finally:
            conn.close()
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route("/api/watchlist", methods=['POST', 'DELETE'])
@login_required
def manage_watchlist():
    try:
        data = request.json
        media_id = data.get('media_id')
        priority = data.get('priority', 1)

        if not media_id:
            return jsonify({'error': 'Missing media_id'}), 400

        conn = get_db_connection()
        try:
            if request.method == 'POST':
                conn.execute('''
                    INSERT OR IGNORE INTO watchlist 
                    (user_id, media_id, priority, date_added)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ''', [current_user.id, media_id, priority])
            else:  # DELETE
                conn.execute('''
                    DELETE FROM watchlist
                    WHERE user_id = ? AND media_id = ?
                ''', [current_user.id, media_id])
            
            conn.commit()
            return jsonify({'success': True})
        finally:
            conn.close()
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route("/api/watch-history", methods=['POST'])
@login_required
def add_to_history():
    try:
        if request.is_json:
            data = request.json
        else:
            data = request.form
            
        media_id = data.get('media_id')

        if not media_id:
            return jsonify({'error': 'Missing media_id'}), 400

        conn = get_db_connection()
        try:
            conn.execute('''
                INSERT OR REPLACE INTO watch_history 
                (user_id, media_id, watch_date)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            ''', [current_user.id, media_id])
            
            conn.commit()
            return jsonify({'success': True})
        finally:
            conn.close()
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
        # Handle both JSON and form data
        if request.is_json:
            data = request.json
        else:
            data = request.form

        media_id = data.get('media_id')
        rating = data.get('rating')

        if not media_id or rating is None:
            return jsonify({'error': 'Missing media_id or rating'}), 400

        try:
            rating = int(rating)
            if not (1 <= rating <= 10):
                raise ValueError
        except (TypeError, ValueError):
            return jsonify({'error': 'Rating must be an integer between 1 and 10'}), 400

        conn = get_db_connection()
        try:
            # First, check if there's a watch history entry
            watch_history = conn.execute('''
                SELECT 1 FROM watch_history 
                WHERE user_id = ? AND media_id = ?
            ''', [current_user.id, media_id]).fetchone()

            # If no watch history entry exists, create one
            if not watch_history:
                conn.execute('''
                    INSERT INTO watch_history 
                    (user_id, media_id, rating, watch_date)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ''', [current_user.id, media_id, rating])
            else:
                # Update existing watch history entry
                conn.execute('''
                    UPDATE watch_history
                    SET rating = ?
                    WHERE user_id = ? AND media_id = ?
                ''', [rating, current_user.id, media_id])
            
            conn.commit()
            return jsonify({
                'success': True,
                'message': 'Rating updated successfully'
            })

        except sqlite3.Error as e:
            conn.rollback()
            return jsonify({
                'error': f'Database error: {str(e)}'
            }), 500
        finally:
            conn.close()

    except Exception as e:
        return jsonify({
            'error': f'Error updating rating: {str(e)}'
        }), 400
    
@app.route("/profile")
@login_required
def profile():
    # Get user's watch history
    watch_history = query_db("""
        SELECT 
            m.id,
            m.title,
            m.year,
            m.type,
            m.poster_url,
            wh.watch_date,
            wh.rating,
            CASE WHEN f.id IS NOT NULL THEN 1 ELSE 0 END as is_favorite
        FROM watch_history wh
        JOIN media m ON wh.media_id = m.id
        LEFT JOIN favorites f ON f.item_id = m.id 
            AND f.user_id = wh.user_id 
            AND f.item_type = 'media'
        WHERE wh.user_id = ?
        ORDER BY wh.watch_date DESC
    """, [current_user.id])

    # Get user's watchlist
    watchlist = query_db("""
        SELECT 
            m.id,
            m.title,
            m.year,
            m.type,
            m.poster_url,
            w.priority,
            w.date_added,
            CASE WHEN f.id IS NOT NULL THEN 1 ELSE 0 END as is_favorite
        FROM watchlist w
        JOIN media m ON w.media_id = m.id
        LEFT JOIN favorites f ON f.item_id = m.id 
            AND f.user_id = w.user_id 
            AND f.item_type = 'media'
        WHERE w.user_id = ?
        ORDER BY w.priority ASC, w.date_added DESC
    """, [current_user.id])

    return render_template("profile.html", 
                         watch_history=watch_history, 
                         watchlist=watchlist)
    
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