# app.py
import sqlite3
import random
import json # Needed for handling seen_challenges list
import os
import base64

# Ensure render_template is imported
from flask import Flask, render_template, request, jsonify, session, g, redirect, url_for, flash
from flask_limiter import Limiter
# Import Flask-Login components
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
# Import your User model
from app_models import User
# Import password hashing utilities
from werkzeug.security import generate_password_hash, check_password_hash

# --- Configuration ---
DATABASE = 'auditor_challenges.db'
SECRET_KEY = os.environ.get('SECRET_KEY', os.urandom(24))

# Scoring Rules
SCORE_POINTS = {'easy': 15, 'medium': 20, 'hard': 25, 'insane': 30}
PENALTY_DIFF = -5
# --- End Configuration ---

app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY
app.config['DATABASE'] = DATABASE

# --- Flask-Login Setup ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' # Route function name for login page
login_manager.login_message = "Please log in to access this page."
login_manager.login_message_category = "info" # Use 'info' or other Bootstrap category

# --- Flask-Limiter Setup ---
def get_current_user_id():
    """
    Key function for Flask-Limiter to identify the user.
    Returns the string representation of the current user's ID.
    """
    if current_user and current_user.is_authenticated:
        return str(current_user.id)
    # Fallback: Should not happen for @login_required routes
    # but good to have a default if limiter is used elsewhere without login.
    return request.remote_addr

limiter = Limiter(
    app=app,
    key_func=get_current_user_id,
    # To apply limits ONLY to specific routes, OMIT `default_limits`
    # or set it to an empty list:
    default_limits=[],  # This ensures no global rate limits are applied by default
    storage_uri="memory://",
    # Reminder: "memory://" storage has limitations with multiple Gunicorn workers
    # for accurate distributed counting. Consider Redis for production.
)

@login_manager.user_loader
def load_user(user_id):
    """Loads a user object from the database given their ID."""
    print(f"--- Attempting to load user with ID: {user_id} ---")
    db = get_db()
    if not db:
        print("Error: Database connection not available in user_loader.")
        return None
    try:
        # Query the users table using the user_id
        user_row = query_db("SELECT id, username, password_hash FROM users WHERE id = ?", [int(user_id)], one=True) # Ensure ID is integer
        if user_row:
            print(f"User found in DB: {user_row['username']}")
            # Create and return a User object using the data from the database
            user_obj = User(id=user_row['id'], username=user_row['username'], password_hash=user_row['password_hash'])
            return user_obj
        else:
            print(f"User with ID {user_id} not found in database.")
            return None
    except Exception as e:
        print(f"Error loading user {user_id}: {e}")
        return None
# --- End Flask-Login Setup ---


# --- Database Handling ---
def get_db():
    """Connects to the specific database."""
    if 'db' not in g:
        try:
            db_path = app.config['DATABASE']
            g.db = sqlite3.connect(db_path)
            # Keep default row factory (tuples) for cursor, convert in query_db/execute_db
            print(f"Database connection established to: {db_path}")
        except sqlite3.Error as e:
            print(f"Database connection error: {e}")
            g.db = None
    return g.db

@app.teardown_appcontext
def close_db(exception):
    """Closes the database again at the end of the request."""
    db = g.pop('db', None)
    if db is not None:
        db.close()
        print("Database connection closed.")

def query_db(query, args=(), one=False):
    """Queries the database and returns results as dictionaries."""
    db = get_db()
    if db is None:
        print("Error: Cannot query database, connection not available.")
        return None
    results_as_dicts = []
    try:
        cur = db.cursor() # Use default cursor
        cur.execute(query, args)
        # Fetch column names to build dictionaries
        column_names = [description[0] for description in cur.description] if cur.description else []
        rows = cur.fetchall() # Fetch all results as tuples
        cur.close()

        # Convert each row (tuple) to a dictionary
        for row in rows:
            results_as_dicts.append(dict(zip(column_names, row)))

        if one:
            return results_as_dicts[0] if results_as_dicts else None
        else:
            return results_as_dicts
    except sqlite3.Error as e:
        print(f"Database query error: {e}")
        print(f"Query: {query} Args: {args}")
        return None
    except Exception as e:
        print(f"Unexpected error during query_db: {e}")
        return None

def execute_db(query, args=()):
    """Executes a query that modifies the database (INSERT, UPDATE, DELETE)."""
    db = get_db()
    if db is None:
        print("Error: Cannot execute query, database connection not available.")
        return False # Indicate failure
    try:
        cur = db.cursor()
        cur.execute(query, args)
        db.commit() # Commit changes for modification queries
        cur.close()
        print(f"Executed modification query successfully: {query} Args: {args}")
        return True # Indicate success
    except sqlite3.Error as e:
        db.rollback() # Rollback changes on error
        print(f"Database execution error: {e}")
        print(f"Query: {query} Args: {args}")
        return False # Indicate failure
    except Exception as e:
        db.rollback()
        print(f"Unexpected error during execute_db: {e}")
        return False

# --- Helper Function to Get User Progress ---
def get_user_progress(user_id):
    """Fetches user progress data or returns defaults if not found."""
    progress = query_db("SELECT total_score, completed_count, seen_challenges FROM user_progress WHERE user_id = ?", [user_id], one=True)
    if progress:
        # Safely parse seen_challenges JSON
        try:
            # Use .get with default '[]' before parsing
            seen_list = json.loads(progress.get('seen_challenges', '[]'))
            # Ensure it's actually a list after parsing
            if not isinstance(seen_list, list):
                print(f"Warning: Parsed seen_challenges for user {user_id} is not a list ({type(seen_list)}). Resetting.")
                seen_list = []
        except (json.JSONDecodeError, TypeError) as e:
            print(f"Warning: Could not parse seen_challenges JSON for user {user_id}. Content: '{progress.get('seen_challenges', '')}'. Error: {e}. Resetting.")
            seen_list = []
        return {
            # Use .get with defaults for score/count as well
            'total_score': progress.get('total_score', 0),
            'completed_count': progress.get('completed_count', 0),
            'seen_challenges': seen_list
        }
    else:
        # This case should ideally not happen if progress row is created on registration
        print(f"Warning: No progress row found for user {user_id} in user_progress table. Returning defaults.")
        # Optionally, create the row here if it's missing
        # execute_db("INSERT OR IGNORE INTO user_progress (user_id) VALUES (?)", (user_id,))
        return {'total_score': 0, 'completed_count': 0, 'seen_challenges': []}

# --- Routes ---

# Add this inside the landing() function in app.py

@app.route('/')
def landing():
    """Renders the landing page, including top leaderboard data."""
    print("--- Accessing landing route ('/') ---")

    # --- Fetch Leaderboard Data ---
    limit = 5 # Show top 5 on the landing page, for example
    leaderboard_data = [] # Default to empty list
    sql_query = """
        SELECT u.username, up.total_score, up.completed_count
        FROM user_progress up
        JOIN users u ON up.user_id = u.id
        ORDER BY up.total_score DESC, up.completed_count DESC
        LIMIT ?
    """
    try:
        top_users = query_db(sql_query, [limit])
        if top_users:
            leaderboard_data = top_users
        print(f"Fetched top {len(leaderboard_data)} users for landing page leaderboard.")
    except Exception as e:
        print(f"Error fetching leaderboard data for landing page: {e}")
        # Don't necessarily flash a message here, just show empty leaderboard
    # --- End Fetch Leaderboard Data ---

    # Pass the leaderboard data to the template
    return render_template('landing.html', leaderboard=leaderboard_data)

@app.route('/ctf')
@login_required # Require login to access the CTF page
def ctf_app():
    """Renders the main CTF application page (lab.html)."""
    print(f"--- Accessing CTF app route ('/ctf') for user: {current_user.username} (ID: {current_user.id}) ---")

    # Fetch progress for the currently logged-in user from the database
    user_progress = get_user_progress(current_user.id)
    initial_score = user_progress['total_score']
    initial_completed = user_progress['completed_count']

    print(f"User {current_user.username}: Initial Score={initial_score}, Completed={initial_completed}")

    print("Fetching distinct vulnerability options for CTF app...")
    vulnerability_options = query_db(
        "SELECT DISTINCT cwe_id, cwe_name FROM challenges ORDER BY cwe_name"
    )
    if vulnerability_options is None: vulnerability_options = []
    print(f"Fetched {len(vulnerability_options)} distinct options.")

    # Pass user's actual initial score/completed count from DB
    return render_template('lab.html',
                           vulnerability_options=vulnerability_options,
                           initial_score=initial_score,
                           initial_completed=initial_completed,
                           PENALTY_DIFF=PENALTY_DIFF
                           )

# --- Other Static Page Routes (Learn, Sponsors) ---
@app.route('/learn')
def learn_page():
    print("--- Accessing learn route ('/learn') ---")
    return render_template('learn.html')

@app.route('/sponsors')
def sponsors_page():
    print("--- Accessing sponsors route ('/sponsors') ---")
    return render_template('sponsors.html')


# --- API Routes ---
@app.route('/get_challenge/<difficulty>')
@login_required # Require login to get challenges
def get_challenge(difficulty):
    """Gets a random challenge, tracking seen challenges per user in DB."""
    print(f"\n--- Inside /get_challenge for user {current_user.username} (requesting difficulty: {difficulty}) ---")

    # Fetch user's specific progress, including seen challenges from DB
    user_progress = get_user_progress(current_user.id)
    seen_ids = user_progress['seen_challenges'] # This is now a Python list
    print(f"User {current_user.username}'s seen_challenges from DB: {seen_ids}")

    placeholders = ','.join('?' * len(seen_ids))
    not_in_clause = f"AND id NOT IN ({placeholders})" if seen_ids else ""

    # Ensure title is selected if you added it to the DB
    sql_query = f"""
        SELECT id, title, vulnerable_code, difficulty, cwe_id, cwe_name, cve_id
        FROM challenges
        WHERE difficulty = ? {not_in_clause}
        ORDER BY RANDOM() LIMIT 1
    """
    args = [difficulty] + seen_ids # Use requested difficulty
    print(f"Executing SQL: {sql_query} with args: {args}")
    challenge_data = query_db(sql_query, args, one=True)
    print(f"Query result: {challenge_data}")

    if challenge_data:
        challenge_id = challenge_data['id']
        # Update user's seen challenges in the database only if it's a new one
        if challenge_id not in seen_ids:
             seen_ids.append(challenge_id)
             try:
                 # Convert updated list back to JSON string for storage
                 seen_challenges_json = json.dumps(seen_ids)
                 update_seen_sql = "UPDATE user_progress SET seen_challenges = ? WHERE user_id = ?"
                 success = execute_db(update_seen_sql, (seen_challenges_json, current_user.id))
                 if success:
                      print(f"Updated seen_challenges in DB for user {current_user.id}: {seen_challenges_json}")
                 else:
                      # Log error but don't necessarily block the user
                      print(f"Error updating seen_challenges in DB for user {current_user.id}")
             except TypeError as e:
                  print(f"Error serializing seen_challenges list to JSON for user {current_user.id}: {e}")
             except Exception as e: # Catch other potential errors during DB update
                  print(f"Unexpected error updating seen_challenges for user {current_user.id}: {e}")


        # Prepare response data
        response_data = {
            "id": challenge_data['id'],
            "title": challenge_data.get('title', f"Challenge #{challenge_id}"), # Default title
            "vulnerable_code": challenge_data['vulnerable_code'],
            "difficulty": challenge_data['difficulty'],
            "correct_cwe": challenge_data['cwe_id'],
            "correct_cwe_name": challenge_data['cwe_name'],
            "cve_id": challenge_data.get('cve_id') # Use .get for optional fields
        }
        return jsonify(response_data)
    else:
        print(f"No suitable challenge found for user {current_user.username} and difficulty {difficulty}.")
        # Return 404 if no challenges are left for this user/difficulty combo
        return jsonify({"error": f"No more challenges found for difficulty '{difficulty}'"}), 404


@app.route('/get_diff/<int:challenge_id>')
@login_required # Require login to get diff
def get_diff(challenge_id):
    """Gets the fixed code for a specific challenge."""
    # Check if user has actually seen this challenge? Optional.
    diff_data = query_db("SELECT fixed_code FROM challenges WHERE id = ?", [challenge_id], one=True)
    if diff_data:
        return jsonify({"fixed_code": diff_data.get('fixed_code')}) # Use .get
    else:
        return jsonify({"error": "Challenge not found"}), 404

@app.route('/submit_answer', methods=['POST'])
@login_required # Require login to submit answers
@limiter.limit("5 per minute")   # THIS SPECIFIC LIMIT APPLIES ONLY TO submit_answer
def submit_answer():
    """Evaluates the user's answer and updates their progress in the DB."""
    print(f"--- Inside /submit_answer for user {current_user.username} ---")
    data = request.get_json()
    if not data: return jsonify({"error": "Invalid request"}), 400

    challenge_id = data.get('challenge_id')
    selected_cwe_b64 = data.get('selected_cwe')
    used_diff = data.get('used_diff', False)

    if not challenge_id or selected_cwe is None: return jsonify({"error": "Missing data"}), 400

    try:
        selected_cwe = base64.b64decode(selected_cwe_b64).decode('utf-8')
    except Exception as e:
        app.logger.error(f"Base64 decoding failed for '{selected_cwe_b64}': {e}")
    return jsonify({"error": "Invalid answer format"}), 400

    # Get challenge info
    challenge_info = query_db(
        "SELECT difficulty, cwe_id, cwe_name, solution FROM challenges WHERE id = ?",
        [challenge_id], one=True
    )
    if not challenge_info: return jsonify({"error": "Challenge not found"}), 404

    # --- Scoring ---
    correct_cwe_id = challenge_info['cwe_id']
    correct_cwe_name = challenge_info['cwe_name']
    difficulty = challenge_info['difficulty']
    is_correct = (selected_cwe == correct_cwe_id)
    score_earned = 0

    if is_correct:
        score_earned += SCORE_POINTS.get(difficulty, 15) # Use actual difficulty score
    if used_diff:
        score_earned += PENALTY_DIFF
    score_earned = max(0, score_earned) # Ensure score >= 0 for this attempt
    print(f"Challenge {challenge_id}: Correct={is_correct}, Score Earned={score_earned}")

    # --- Update User Progress in DB ---
    user_id = current_user.id
    # Fetch current progress first to avoid race conditions if possible (though unlikely here)
    user_progress = get_user_progress(user_id)
    # Calculate new totals based on fetched progress
    new_total_score = user_progress['total_score'] + score_earned
    new_completed_count = user_progress['completed_count'] + (1 if is_correct else 0)

    # Update the user's record in the database
    update_sql = """
        UPDATE user_progress
        SET total_score = ?, completed_count = ?
        WHERE user_id = ?
    """
    success = execute_db(update_sql, (new_total_score, new_completed_count, user_id))

    if not success:
        print(f"CRITICAL Error: Failed to update progress in DB for user {user_id}")
        # Depending on requirements, you might return an error here
        # or flash a message to the user on the next request.
        # For now, we proceed but the score won't be saved.

    # --- Prepare Response ---
    # Return the *updated* totals reflecting this submission
    response = {
        "correct": is_correct,
        "score_earned": score_earned,
        "total_score": new_total_score, # Return the new total score
        "completed_count": new_completed_count, # Return the new completed count
        "solution": challenge_info['solution'],
        "correct_cwe": correct_cwe_id,
        "correct_cwe_name": correct_cwe_name
    }
    print(f"Submit Response for user {user_id}: {response}")
    return jsonify(response)


# --- Authentication Routes ---
# (Register, Login, Logout routes remain unchanged from previous version)
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated: return redirect(url_for('ctf_app'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        error = None
        if not username: error = 'Username is required.'
        elif not password: error = 'Password is required.'
        else:
            existing_user = query_db("SELECT id FROM users WHERE username = ?", [username], one=True)
            if existing_user: error = f"Username '{username}' is already taken."
        if error is None:
            new_user = User(id=None, username=username, password_hash=None)
            new_user.set_password(password)
            insert_user_sql = "INSERT INTO users (username, password_hash) VALUES (?, ?)"
            success = execute_db(insert_user_sql, (new_user.username, new_user.password_hash))
            if success:
                user_info = query_db("SELECT id FROM users WHERE username = ?", [username], one=True)
                if user_info:
                    user_id = user_info['id']
                    # Ensure progress row is created with defaults
                    execute_db("INSERT OR IGNORE INTO user_progress (user_id) VALUES (?)", (user_id,))
                    flash('Registration successful! Please log in.', 'success')
                    return redirect(url_for('login'))
                else: error = "Registration succeeded but failed to retrieve user ID."
            else: error = "Registration failed. Please try again."
        if error: flash(error, 'danger')
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated: return redirect(url_for('ctf_app'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False
        error = None
        if not username or not password: error = "Username and password are required."
        else:
            user_row = query_db("SELECT id, username, password_hash FROM users WHERE username = ?", [username], one=True)
            if user_row:
                user_obj = User(id=user_row['id'], username=user_row['username'], password_hash=user_row['password_hash'])
                if user_obj.check_password(password):
                    login_user(user_obj, remember=remember)
                    flash('Logged in successfully!', 'success')
                    next_page = request.args.get('next')
                    # Ensure next_page is safe - basic check here, more robust needed for production
                    if next_page and not next_page.startswith('/'): next_page = None
                    return redirect(next_page or url_for('ctf_app'))
                else: error = "Invalid username or password."
            else: error = "Invalid username or password."
        if error: flash(error, 'danger')
    return render_template('login.html')


@app.route('/profile')
@login_required # Ensure only logged-in users can see this
def profile():
    """Displays the user's profile page with their progress."""
    print(f"--- Accessing profile route ('/profile') for user: {current_user.username} ---")

    # Get the user's progress from the database using the helper function
    # This fetches score, completed count, and seen challenges list
    user_progress = get_user_progress(current_user.id)

    # Pass the current_user object (provides username, id from Flask-Login)
    # and their progress dictionary to the template.
    return render_template('profile.html',
                           user=current_user,
                           progress=user_progress)

# --- End Profile Route ---

@app.route('/leaderboard')
def leaderboard():
    """Displays the top users based on score."""
    print("--- Accessing leaderboard route ('/leaderboard') ---")
    limit = 10 # Number of top users to display

    # Query to get top users: join users and user_progress, order by score
    sql_query = """
        SELECT u.username, up.total_score, up.completed_count
        FROM user_progress up
        JOIN users u ON up.user_id = u.id
        ORDER BY up.total_score DESC, up.completed_count DESC -- Tie-break by completed count
        LIMIT ?
    """
    try:
        top_users = query_db(sql_query, [limit])
        if top_users is None:
            top_users = [] # Ensure it's an empty list on error
            flash("Could not retrieve leaderboard data.", "warning")
        print(f"Fetched top {len(top_users)} users for leaderboard.")
    except Exception as e:
        print(f"Error fetching leaderboard data: {e}")
        top_users = []
        flash("An error occurred while fetching the leaderboard.", "danger")

    # Pass the ranked list to the template
    return render_template('leaderboard.html', leaderboard=top_users)

# --- End Leaderboard Route ---
@app.route('/logout', methods=['POST']) 
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('landing'))

# --- End Authentication Routes ---

# --- Main Execution ---
if __name__ == '__main__':
    print("Starting Flask server...")
    # Set debug=False for production
    app.run(debug=True, host='0.0.0.0', port=5000)

