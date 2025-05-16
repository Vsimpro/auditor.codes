# app.py
import sqlite3
import random
import json
import os
import base64

from flask import Flask, render_template, request, jsonify, session, g, redirect, url_for, flash
from flask_limiter import Limiter
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from app_models import User
from werkzeug.security import generate_password_hash, check_password_hash

DATABASE = 'auditor_challenges.db'
SECRET_KEY = os.environ.get('SECRET_KEY', os.urandom(24))

SCORE_POINTS = {'easy': 15, 'medium': 20, 'hard': 25, 'insane': 30}
PENALTY_DIFF = -5

app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY
app.config['DATABASE'] = DATABASE

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = "Please log in to access this page."
login_manager.login_message_category = "info"

def get_current_user_id():
    if current_user and current_user.is_authenticated:
        return str(current_user.id)
    return request.remote_addr

limiter = Limiter(
    app=app,
    key_func=get_current_user_id,
    default_limits=[],
    storage_uri="memory://",
)

@login_manager.user_loader
def load_user(user_id):
    db = get_db()
    if not db:
        return None
    try:
        user_row = query_db("SELECT id, username, password_hash FROM users WHERE id = ?", [int(user_id)], one=True)
        if user_row:
            user_obj = User(id=user_row['id'], username=user_row['username'], password_hash=user_row['password_hash'])
            return user_obj
        else:
            return None
    except Exception as e:
        app.logger.error(f"Error loading user {user_id}: {e}")
        return None

def get_db():
    if 'db' not in g:
        try:
            db_path = app.config['DATABASE']
            g.db = sqlite3.connect(db_path)
        except sqlite3.Error as e:
            app.logger.error(f"Database connection error: {e}")
            g.db = None
    return g.db

@app.teardown_appcontext
def close_db(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def query_db(query, args=(), one=False):
    db = get_db()
    if db is None:
        return None
    results_as_dicts = []
    try:
        cur = db.cursor()
        cur.execute(query, args)
        column_names = [description[0] for description in cur.description] if cur.description else []
        rows = cur.fetchall()
        cur.close()
        for row in rows:
            results_as_dicts.append(dict(zip(column_names, row)))
        if one:
            return results_as_dicts[0] if results_as_dicts else None
        else:
            return results_as_dicts
    except sqlite3.Error as e:
        app.logger.error(f"Database query error: {e} Query: {query} Args: {args}")
        return None
    except Exception as e:
        app.logger.error(f"Unexpected error during query_db: {e}")
        return None

def execute_db(query, args=()):
    db = get_db()
    if db is None:
        return False
    try:
        cur = db.cursor()
        cur.execute(query, args)
        db.commit()
        cur.close()
        return True
    except sqlite3.Error as e:
        db.rollback()
        app.logger.error(f"Database execution error: {e} Query: {query} Args: {args}")
        return False
    except Exception as e:
        db.rollback()
        app.logger.error(f"Unexpected error during execute_db: {e}")
        return False

def get_user_progress(user_id):
    progress = query_db("SELECT total_score, completed_count, seen_challenges FROM user_progress WHERE user_id = ?", [user_id], one=True)
    if progress:
        try:
            seen_list = json.loads(progress.get('seen_challenges', '[]'))
            if not isinstance(seen_list, list):
                seen_list = []
        except (json.JSONDecodeError, TypeError) as e:
            app.logger.warning(f"Could not parse seen_challenges JSON for user {user_id}. Content: '{progress.get('seen_challenges', '')}'. Error: {e}. Resetting.")
            seen_list = []
        return {
            'total_score': progress.get('total_score', 0),
            'completed_count': progress.get('completed_count', 0),
            'seen_challenges': seen_list
        }
    else:
        app.logger.warning(f"No progress row found for user {user_id} in user_progress table. Returning defaults.")
        return {'total_score': 0, 'completed_count': 0, 'seen_challenges': []}

@app.route('/')
def landing():
    limit = 5
    leaderboard_data = []
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
    except Exception as e:
        app.logger.error(f"Error fetching leaderboard data for landing page: {e}")
    return render_template('landing.html', leaderboard=leaderboard_data)

@app.route('/ctf')
@login_required
def ctf_app():
    user_progress = get_user_progress(current_user.id)
    initial_score = user_progress['total_score']
    initial_completed = user_progress['completed_count']
    vulnerability_options = query_db(
        "SELECT DISTINCT cwe_id, cwe_name FROM challenges ORDER BY cwe_name"
    )
    if vulnerability_options is None: vulnerability_options = []
    return render_template('lab.html',
                           vulnerability_options=vulnerability_options,
                           initial_score=initial_score,
                           initial_completed=initial_completed,
                           PENALTY_DIFF=PENALTY_DIFF)

@app.route('/learn')
def learn_page():
    return render_template('learn.html')

@app.route('/sponsors')
def sponsors_page():
    return render_template('sponsors.html')

@app.route('/get_challenge/<difficulty>')
@login_required
def get_challenge(difficulty):
    user_progress = get_user_progress(current_user.id)
    seen_ids = user_progress['seen_challenges']
    placeholders = ','.join('?' * len(seen_ids))
    not_in_clause = f"AND id NOT IN ({placeholders})" if seen_ids else ""
    sql_query = f"""
        SELECT id, title, vulnerable_code, difficulty, cwe_id, cwe_name, cve_id
        FROM challenges
        WHERE difficulty = ? {not_in_clause}
        ORDER BY RANDOM() LIMIT 1
    """
    args = [difficulty] + seen_ids
    challenge_data = query_db(sql_query, args, one=True)
    if challenge_data:
        challenge_id = challenge_data['id']
        if challenge_id not in seen_ids:
            seen_ids.append(challenge_id)
            try:
                seen_challenges_json = json.dumps(seen_ids)
                update_seen_sql = "UPDATE user_progress SET seen_challenges = ? WHERE user_id = ?"
                execute_db(update_seen_sql, (seen_challenges_json, current_user.id))
            except Exception as e:
                app.logger.error(f"Error updating seen_challenges for user {current_user.id}: {e}")
        response_data = {
            "id": challenge_data['id'],
            "title": challenge_data.get('title', f"Challenge #{challenge_data['id']}"),
            "vulnerable_code": challenge_data['vulnerable_code'],
            "difficulty": challenge_data['difficulty'],
            "correct_cwe": challenge_data['cwe_id'],
            "correct_cwe_name": challenge_data['cwe_name'],
            "cve_id": challenge_data.get('cve_id')
        }
        return jsonify(response_data)
    else:
        return jsonify({"error": f"No more challenges found for difficulty '{difficulty}'"}), 404

@app.route('/get_diff/<int:challenge_id>')
@login_required
def get_diff(challenge_id):
    diff_data = query_db("SELECT fixed_code FROM challenges WHERE id = ?", [challenge_id], one=True)
    if diff_data:
        return jsonify({"fixed_code": diff_data.get('fixed_code')})
    else:
        return jsonify({"error": "Challenge not found"}), 404

@app.route('/submit_answer', methods=['POST'])
@login_required
@limiter.limit("5 per minute")
def submit_answer():
    data = request.get_json()
    if not data:
        app.logger.error("No JSON data received in /submit_answer")
        return jsonify({"error": "Invalid request data"}), 400

    challenge_id = data.get('challenge_id')
    selected_cwe_b64 = data.get('selected_cwe')
    used_diff = data.get('used_diff', False)

    if not challenge_id or selected_cwe_b64 is None:
        app.logger.warning(f"Missing challenge_id or selected_cwe_b64. Challenge ID: {challenge_id}, Encoded CWE: {selected_cwe_b64}")
        return jsonify({"error": "Missing challenge ID or answer data"}), 400

    try:
        selected_cwe = base64.b64decode(selected_cwe_b64).decode('utf-8')
        if not selected_cwe: # Check if the decoded string is empty
             app.logger.warning(f"Decoded selected_cwe is empty for challenge_id: {challenge_id}, b64_value: {selected_cwe_b64}")
             return jsonify({"error": "Decoded answer is empty"}), 400
    except Exception as e:
        app.logger.error(f"Base64 decoding failed for value '{selected_cwe_b64}'. Error: {e}")
        return jsonify({"error": "Invalid answer format. Decoding failed."}), 400

    app.logger.info(f"Processing answer for Challenge ID: {challenge_id}, Decoded CWE: {selected_cwe}, Used Diff: {used_diff}")

    challenge_info = query_db(
        "SELECT difficulty, cwe_id, cwe_name, solution FROM challenges WHERE id = ?",
        [challenge_id], one=True
    )
    if not challenge_info:
        app.logger.error(f"Challenge with ID {challenge_id} not found in database.")
        return jsonify({"error": "Challenge not found"}), 404

    correct_cwe_id = challenge_info['cwe_id']
    correct_cwe_name = challenge_info['cwe_name']
    difficulty = challenge_info['difficulty']
    is_correct = (selected_cwe == correct_cwe_id)
    score_earned = 0

    if is_correct:
        score_earned += SCORE_POINTS.get(difficulty, 15)
    if used_diff:
        score_earned += PENALTY_DIFF
    score_earned = max(0, score_earned)

    user_id = current_user.id
    user_progress = get_user_progress(user_id)
    new_total_score = user_progress['total_score'] + score_earned
    new_completed_count = user_progress['completed_count'] + (1 if is_correct else 0)

    update_sql = """
        UPDATE user_progress
        SET total_score = ?, completed_count = ?
        WHERE user_id = ?
    """
    success = execute_db(update_sql, (new_total_score, new_completed_count, user_id))

    if not success:
        app.logger.critical(f"Failed to update progress in DB for user {user_id}")
        # Optionally return a specific error if DB update fails critically
        # return jsonify({"error": "Failed to save progress"}), 500


    response_data = {
        "correct": is_correct,
        "score_earned": score_earned,
        "total_score": new_total_score,
        "completed_count": new_completed_count,
        "solution": challenge_info['solution'],
        "correct_cwe": correct_cwe_id,
        "correct_cwe_name": correct_cwe_name
    }
    return jsonify(response_data)

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
                    if next_page and not next_page.startswith('/'): next_page = None
                    return redirect(next_page or url_for('ctf_app'))
                else: error = "Invalid username or password."
            else: error = "Invalid username or password."
        if error: flash(error, 'danger')
    return render_template('login.html')

@app.route('/profile')
@login_required
def profile():
    user_progress = get_user_progress(current_user.id)
    return render_template('profile.html',
                           user=current_user,
                           progress=user_progress)

@app.route('/leaderboard')
def leaderboard():
    limit = 10
    sql_query = """
        SELECT u.username, up.total_score, up.completed_count
        FROM user_progress up
        JOIN users u ON up.user_id = u.id
        ORDER BY up.total_score DESC, up.completed_count DESC
        LIMIT ?
    """
    top_users = query_db(sql_query, [limit])
    if top_users is None:
        top_users = []
        flash("Could not retrieve leaderboard data.", "warning")
    return render_template('leaderboard.html', leaderboard=top_users)

@app.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('landing'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
