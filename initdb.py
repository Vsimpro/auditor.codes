# init_db.py
import sqlite3
import os

# --- Configuration ---
# IMPORTANT: Make sure this matches the DATABASE variable in your app.py
DATABASE_FILE = 'auditor_challenges.db'
# --- End Configuration ---

def initialize_database(reset_users=True):
    """
    Initializes the database. Creates tables if they don't exist.
    Optionally drops and recreates user-related tables for a fresh start.
    """
    print(f"Attempting to connect to database: {DATABASE_FILE}")
    conn = None  # Initialize conn to None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        print("Database connection successful.")

        if reset_users:
            print("Resetting user tables (Dropping users and user_progress)...")
            # Drop tables first (order matters due to foreign key)
            drop_commands = [
                "DROP TABLE IF EXISTS user_progress;",
                "DROP TABLE IF EXISTS users;",
                "DROP INDEX IF EXISTS idx_username;" # Drop index associated with users table
            ]
            for command in drop_commands:
                try:
                    cursor.execute(command)
                    print(f"Executed: {command.strip()}")
                except sqlite3.Error as e:
                    print(f"Error executing DROP command: {e}")
                    print(f"Command: {command}")
            print("User tables dropped.")

        # SQL commands to create tables (IF NOT EXISTS ensures safety,
        # but after dropping, they will always be created if reset_users=True)
        create_commands = [
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """,
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_username ON users (username);
            """,
            """
            CREATE TABLE IF NOT EXISTS user_progress (
                user_id INTEGER PRIMARY KEY,
                total_score INTEGER DEFAULT 0,
                completed_count INTEGER DEFAULT 0,
                seen_challenges TEXT DEFAULT '[]',
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE -- Optional: Delete progress if user is deleted
            );
            """,
            # --- IMPORTANT ---
            # Add CREATE TABLE IF NOT EXISTS for 'challenges' here
            # to ensure it's never accidentally dropped and always exists.
            """
            CREATE TABLE IF NOT EXISTS challenges (
               id INTEGER PRIMARY KEY,
               title TEXT,
               vulnerable_code TEXT NOT NULL,
               fixed_code TEXT,
               difficulty TEXT NOT NULL,
               cwe_id TEXT NOT NULL,
               cwe_name TEXT,
               cve_id TEXT,
               solution TEXT,
               hint TEXT -- Add other columns as needed
            );
            """
        ]

        print("Executing CREATE TABLE statements...")
        for command in create_commands:
            try:
                cursor.execute(command)
                print(f"Executed: {command.strip().splitlines()[0]}...") # Print first line of command
            except sqlite3.Error as e:
                print(f"Error executing CREATE command: {e}")
                print(f"Command: {command}")

        conn.commit()
        print("Database tables checked/created successfully.")
        if reset_users:
            print("*** User data has been reset. ***")

    except sqlite3.Error as e:
        print(f"Database connection or operation error: {e}")
        if conn:
             conn.rollback() # Rollback any partial changes if error occurs
    finally:
        if conn:
            conn.close()
            print("Database connection closed.")

if __name__ == '__main__':
    # Check if the database file exists before trying to connect
    if not os.path.exists(DATABASE_FILE):
         print(f"Warning: Database file '{DATABASE_FILE}' not found. It will be created.")

    # Set reset_users to True to wipe user data, False to just ensure tables exist
    WIPE_USER_DATA = True
    initialize_database(reset_users=WIPE_USER_DATA)

    if not WIPE_USER_DATA:
        print("\nNOTE: User data was NOT reset. Run with WIPE_USER_DATA=True to clear users.")

