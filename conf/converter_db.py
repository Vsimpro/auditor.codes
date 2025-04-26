# convert_megavul_to_sqlite.py
import json
import sqlite3
import os
import sys
import random
from collections import defaultdict, Counter

# Optional: Import tqdm for progress bar
try:
    from tqdm import tqdm
except ImportError:
    print("Info: 'tqdm' library not found. Progress bar will not be shown.")
    print("You can install it using: pip install tqdm")
    def tqdm(iterable, *args, **kwargs):
        return iterable

print("Converting MegaVul dataset and initializing SQLite database...")
print("This script will REMOVE the existing DB file and create all tables (users, user_progress, challenges).")
print("Applying filters: Must have CVE ID, CWE must be in final list, limiting entries per CWE.")

# --- Configuration ---
JSON_INPUT_FILE = 'megavul_simple.json'
DB_FILE = 'auditor_challenges.db'
MAX_ENTRIES_PER_CWE = 500
TARGET_DIFFICULTY = 'easy'
# --- End Configuration ---

# --- Final Allowed CWE IDs ---
FINAL_ALLOWED_CWE_IDS = {
    "CWE-476", "CWE-787", "CWE-416", "CWE-125", "CWE-20", "CWE-401",
    "CWE-200", "CWE-362", "CWE-190", "CWE-120", "CWE-415", "CWE-835",
    "CWE-369", "CWE-122", "CWE-770", "CWE-287", "CWE-404", "CWE-908",
    "CWE-667", "CWE-284", "CWE-367", "CWE-269", "CWE-843", "CWE-193",
    "CWE-191", "CWE-754", "CWE-704", "CWE-681", "CWE-203", "CWE-129",
    "CWE-682", "CWE-824", "CWE-330", "CWE-121"
}
print(f"Will keep entries matching these {len(FINAL_ALLOWED_CWE_IDS)} CWE IDs (if they also have a CVE).")
print(f"Limiting to {MAX_ENTRIES_PER_CWE} entries per CWE (except CWE-121).")
# --- End Allowed CWE IDs ---

# --- CWE ID to Name Mapping ---
CWE_NAME_MAP = {
    "CWE-476": "NULL Pointer Dereference", "CWE-787": "Out-of-bounds Write",
    "CWE-416": "Use After Free", "CWE-125": "Out-of-bounds Read",
    "CWE-20": "Improper Input Validation", "CWE-401": "Memory Leak",
    "CWE-200": "Information Exposure", "CWE-362": "Race Condition",
    "CWE-190": "Integer Overflow", "CWE-120": "Classic Buffer Overflow",
    "CWE-415": "Double Free", "CWE-835": "Infinite Loop",
    "CWE-369": "Divide By Zero", "CWE-122": "Heap Overflow",
    "CWE-770": "Allocation without Limits", "CWE-287": "Improper Authentication",
    "CWE-404": "Improper Resource Shutdown", "CWE-908": "Use of Uninitialized Resource",
    "CWE-667": "Improper Locking", "CWE-284": "Improper Access Control",
    "CWE-367": "TOCTOU Race Condition", "CWE-269": "Improper Privilege Management",
    "CWE-843": "Type Confusion", "CWE-193": "Off-by-one Error",
    "CWE-191": "Integer Underflow", "CWE-754": "Improper Check for Exceptional Conditions",
    "CWE-704": "Incorrect Type Conversion", "CWE-681": "Incorrect Numeric Conversion",
    "CWE-203": "Observable Discrepancy", "CWE-129": "Improper Validation of Array Index",
    "CWE-682": "Incorrect Calculation", "CWE-824": "Uninitialized Pointer",
    "CWE-330": "Insufficiently Random Values", "CWE-121": "Stack Overflow"
}
print(f"Using CWE_NAME_MAP with {len(CWE_NAME_MAP)} entries.")
# --- End CWE Mapping ---

# --- Load JSON Data ---
print(f"\nReading '{JSON_INPUT_FILE}' file...")
if not os.path.exists(JSON_INPUT_FILE):
    print(f"Error: Input JSON file '{JSON_INPUT_FILE}' not found.")
    sys.exit(1)
try:
    with open(JSON_INPUT_FILE, 'r', encoding='utf-8') as f: data = json.load(f)
    if not isinstance(data, list): raise ValueError("Expected a JSON list")
    print(f"Loaded {len(data)} total entries from JSON.")
except Exception as e:
    print(f"An error occurred reading the JSON file: {e}")
    sys.exit(1)
# --- End JSON Loading ---

# --- Filter Entries by CVE and Allowed CWEs, Group by CWE ---
print("\nFiltering entries by CVE presence and allowed CWEs, grouping by CWE...")
grouped_valid_entries = defaultdict(list)
# (Filtering logic remains the same as before)
processed_count = 0; skipped_no_cve = 0; skipped_wrong_cwe = 0
for item in tqdm(data, desc="Filtering & Grouping"):
    processed_count += 1
    if not isinstance(item, dict): continue
    cve_id = item.get('cve_id')
    if not (cve_id and isinstance(cve_id, str) and cve_id.strip()):
        skipped_no_cve += 1; continue
    cwe_ids = item.get('cwe_ids'); primary_cwe_id = None
    if isinstance(cwe_ids, list) and cwe_ids: primary_cwe_id = str(cwe_ids[0]).strip()
    if primary_cwe_id not in FINAL_ALLOWED_CWE_IDS:
        skipped_wrong_cwe += 1; continue
    if not (item.get('is_vul') and item.get('func_before') and item.get('func')): continue
    grouped_valid_entries[primary_cwe_id].append(item)

print(f"\nProcessed {processed_count} entries.")
print(f"Skipped {skipped_no_cve} entries without a valid CVE.")
print(f"Skipped {skipped_wrong_cwe} entries with non-allowed CWE IDs.")
print(f"Grouped {sum(len(v) for v in grouped_valid_entries.values())} valid entries into {len(grouped_valid_entries)} CWE groups.")
# --- End Filtering ---

# --- Limit Entries per CWE ---
print(f"\nLimiting entries per CWE (Max: {MAX_ENTRIES_PER_CWE}, except CWE-121)...")
entries_to_insert = []
final_counts = Counter()
# (Limiting logic remains the same as before)
for cwe_id, entries in grouped_valid_entries.items():
    limit = MAX_ENTRIES_PER_CWE; is_special_case = False
    if cwe_id == "CWE-121": limit = len(entries); is_special_case = True; print(f"  - Keeping all {limit} entries for CWE-121.")
    elif len(entries) > limit: print(f"  - CWE {cwe_id}: Found {len(entries)}, shuffling and taking {limit}."); random.shuffle(entries); selected_entries = entries[:limit]
    else: print(f"  - CWE {cwe_id}: Found {len(entries)}, keeping all."); selected_entries = entries
    entries_to_insert.extend(selected_entries); final_counts[cwe_id] = len(selected_entries)

print(f"\nSelected a total of {len(entries_to_insert)} entries for insertion.")
print("Final counts per CWE:")
for cwe_id, count in sorted(final_counts.items()): print(f"  - {cwe_id}: {count}")
# --- End Limiting ---

# --- Database Setup ---
# Remove existing DB file to ensure a clean start
if os.path.exists(DB_FILE):
    print(f"\nRemoving existing database file: {DB_FILE}")
    try: os.remove(DB_FILE)
    except OSError as e: print(f"Error removing existing database: {e}"); sys.exit(1)

conn = None
try:
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    print(f"Created new database: {DB_FILE}")

    # *** ADDED User and Progress Table Creation ***
    print("\nCreating 'users' and 'user_progress' tables...")
    user_table_commands = [
        """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """,
        """
        CREATE UNIQUE INDEX idx_username ON users (username);
        """,
        """
        CREATE TABLE user_progress (
            user_id INTEGER PRIMARY KEY,
            total_score INTEGER DEFAULT 0,
            completed_count INTEGER DEFAULT 0,
            seen_challenges TEXT DEFAULT '[]',
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        );
        """
    ]
    for command in user_table_commands:
        try:
            cursor.execute(command)
            print(f"Executed: {command.strip().splitlines()[0]}...")
        except sqlite3.Error as e:
            print(f"Error executing user table command: {e}"); print(f"Command: {command}"); conn.close(); sys.exit(1)
    print("User tables created successfully.")
    # *** END User Table Creation ***

    # Create challenges table
    print("\nCreating 'challenges' table...")
    # Use AUTOINCREMENT for challenge ID as well for simplicity
    cursor.execute('''
    CREATE TABLE challenges (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cwe_id TEXT NOT NULL,
        cwe_name TEXT,
        cve_id TEXT,
        difficulty TEXT NOT NULL,
        title TEXT,
        vulnerable_code TEXT NOT NULL,
        fixed_code TEXT,
        description TEXT,
        vulnerability TEXT,
        impact TEXT,
        hint TEXT,
        solution TEXT,
        commit_hash TEXT,
        git_url TEXT
    )
    ''')

    # Create challenges indexes
    print("Creating challenges indexes...")
    cursor.execute('CREATE INDEX idx_difficulty ON challenges(difficulty)')
    cursor.execute('CREATE INDEX idx_cwe_id ON challenges(cwe_id)')
    cursor.execute('CREATE INDEX idx_cve_id ON challenges(cve_id)')

    # --- Insert Challenge Data ---
    print(f"\nInserting {len(entries_to_insert)} selected challenge entries...")
    inserted_count = 0
    error_count = 0

    for item in tqdm(entries_to_insert, desc="Inserting Challenges"):
        try:
            # (Data extraction logic remains the same)
            cwe_ids = item.get('cwe_ids'); primary_cwe_id = str(cwe_ids[0]).strip() if isinstance(cwe_ids, list) and cwe_ids else 'Unknown'
            cwe_name = CWE_NAME_MAP.get(primary_cwe_id, primary_cwe_id)
            cve_id = item.get('cve_id', '').strip()
            difficulty = TARGET_DIFFICULTY
            title = f"{cwe_name} ({cwe_id})"
            if cve_id: title += f" - {cve_id}"
            # Add unique part later if needed, DB ID is now unique
            vulnerability_desc = f"Potential {cwe_name} vulnerability ({cwe_id}). Associated CVE: {cve_id}."
            impact = "Exploitation could lead to various security impacts."
            hint = "Examine data flow, boundary conditions, and resource management."
            solution = "Specific fix depends on the exact code pattern."

            # Insert into database (excluding 'id')
            cursor.execute('''
            INSERT INTO challenges
            (cwe_id, cwe_name, cve_id, difficulty, title, vulnerable_code, fixed_code,
             description, vulnerability, impact, hint, solution, commit_hash, git_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                primary_cwe_id, cwe_name, cve_id, difficulty, title,
                item.get('func_before', ''), item.get('func', ''),
                "Analyze the 'Vulnerable Code' snippet...",
                vulnerability_desc, impact, hint, solution,
                item.get('commit_hash', ''), item.get('git_url', '')
            ))
            inserted_count += 1

            # Commit periodically
            if inserted_count % 1000 == 0:
                conn.commit()
                # print(f"Committed {inserted_count} entries...") # Less verbose

        except Exception as e:
            print(f"\nError processing entry (Commit Hash: {item.get('commit_hash', 'N/A')}): {str(e)}")
            error_count += 1

    # Final commit
    conn.commit()
    print(f"\nChallenge insertion complete.")
    print(f"Successfully inserted: {inserted_count} challenge entries")
    if error_count > 0:
        print(f"Errors encountered during insertion: {error_count} entries")
    print(f"Database saved as: {DB_FILE}")

except sqlite3.Error as e:
    print(f"Database error: {e}")
except Exception as e:
    print(f"An unexpected error occurred: {str(e)}")
finally:
    if conn:
        conn.close()
        print("Database connection closed.")

