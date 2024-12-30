from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from sqlite3 import Error

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'  # Change this to a secure secret key

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Database helper functions
def get_db_connection():
    try:
        conn = sqlite3.connect('movies.db')
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
    return render_template("index.html")

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

@app.route("/preferences", methods=["GET", "POST"])
@login_required
def preferences():
    if request.method == "POST":
        # Get form data
        genres = request.form.getlist('genres')
        min_rating = request.form.get('rating')
        year_from = request.form.get('yearFrom')
        year_to = request.form.get('yearTo')
        languages = request.form.getlist('languages')

        try:
            # Save preferences to database (implement this later)
            flash("Preferences saved successfully!", "preferences-success")
            return redirect(url_for("recommendations"))
        except Exception as e:
            print(e)
            flash("Failed to save preferences", "preferences-error")
            return render_template("movie_preferences.html")

    return render_template("movie_preferences.html")

@app.route("/recommendations")
@login_required
def recommendations():
    page = request.args.get('page', 1, type=int)
    sort_by = request.args.get('sort', 'relevance')
    
    # Dummy data for demonstration
    movies = [
        {
            'id': 1,
            'title': 'Sample Movie 1',
            'poster_url': 'https://via.placeholder.com/300x450',
            'year': 2023,
            'rating': 8.5,
            'overview': 'This is a sample movie overview that demonstrates the plot of the movie...',
            'release_date': '2023-12-25',
            'genres': ['Action', 'Adventure'],
            'cast': ['Actor 1', 'Actor 2', 'Actor 3'],
            'director': 'Director Name'
        },
        {
            'id': 2,
            'title': 'Sample Movie 2',
            'poster_url': 'https://via.placeholder.com/300x450',
            'year': 2023,
            'rating': 7.8,
            'overview': 'Another sample movie overview showing a different storyline...',
            'release_date': '2023-11-15',
            'genres': ['Drama', 'Thriller'],
            'cast': ['Actor 4', 'Actor 5', 'Actor 6'],
            'director': 'Another Director'
        },
        # Add more sample movies as needed
    ]

    selected_genres = ['Action', 'Adventure', 'Sci-Fi']
    min_rating = 7.0
    year_from = 2000
    year_to = 2024
    selected_languages = [
        {'code': 'en', 'name': 'English'},
        {'code': 'es', 'name': 'Spanish'}
    ]

    total_pages = 5

    return render_template('recommendations.html',
                         movies=movies,
                         page=page,
                         total_pages=total_pages,
                         selected_genres=selected_genres,
                         min_rating=min_rating,
                         year_from=year_from,
                         year_to=year_to,
                         selected_languages=selected_languages)

if __name__ == '__main__':
    app.run(debug=True)