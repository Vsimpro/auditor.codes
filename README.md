# Code Auditor CTF ️‍♀️
![image](https://github.com/user-attachments/assets/fdfbbffc-71f9-4463-856d-aca054399a0f)
A web-based Capture The Flag (CTF) platform offering unparalleled depth and breadth in source code auditing challenges. With the largest collection of real-world C/C++ vulnerability examples available anywhere, users analyze authentic code snippets, identify sophisticated security flaws, and master secure coding practices through hands-on experience.
Our comprehensive training environment features thousands of meticulously curated challenges spanning the entire vulnerability spectrum - from classic buffer overflows to the most obscure memory corruption bugs. No other platform provides this level of completeness in source code security education.

## Features ✨

* **Vulnerability Challenges:** Practice identifying various CWEs (Common Weakness Enumerations) in C/C++ code snippets.
* **Multiple Difficulty Levels:** Challenges categorized by difficulty (Easy, Medium, Hard, Insane - *Note: Current implementation might be simplified*).
* **Code Diff View:** Compare vulnerable code side-by-side with a fixed version.
* **User Authentication:** Secure user registration, login, and logout functionality using Flask-Login.
* **Persistent Progress:** User scores and completed challenges are tracked in a database.
* **User Profiles:** View individual scores and completion stats.
* **Leaderboard:** See how you rank against other auditors!
* **Educational Content:** Dedicated "Learn" section (content to be added).
* **Modern UI:** Dark theme with Tailwind CSS for landing/auth pages and Prism.js for code highlighting.
* **Extensive Challenge Dataset:** Features over 7000+ challenges derived from real C/C++ code snippets. *(Based on the excellent [MegaVul dataset](https://github.com/Icyrockton/MegaVul) by Icyrockton)*.

## Tech Stack ️

* **Backend:**
    * Python 3
    * Flask (Web Framework)
    * Flask-Login (User Session Management)
    * Werkzeug (Password Hashing, WSGI utilities)
    * SQLite (Database)
    * Gunicorn (Production WSGI Server - Recommended)
* **Frontend:**
    * HTML5
    * CSS3 (including custom styles)
    * Tailwind CSS (for specific pages like landing/auth)
    * Vanilla JavaScript (DOM manipulation, API calls)
    * Prism.js (Syntax Highlighting)

## Setup & Installation

Follow these steps to set up the project locally for development or testing:

1.  **Clone the Repository:**
    ```bash
    git clone <your-repository-url>
    cd <repository-directory>
    ```

2.  **Create and Activate a Virtual Environment:**
    ```bash
    # Linux/macOS
    python3 -m venv venv
    source venv/bin/activate

    # Windows
    python -m venv venv
    .\venv\Scripts\activate
    ```

3.  **Install Dependencies:**
    * **Create `requirements.txt`:** Make sure you have a `requirements.txt` file listing the necessary packages. It should contain at least:
        ```
        Flask
        Flask-Login
        Werkzeug
        gunicorn # Optional, but recommended for testing production setup
        ```
    * **Install:**
        ```bash
        pip install -r requirements.txt
        ```

4.  **Initialize the Database:**
    * Run the database initialization script to create the necessary SQLite tables (`users`, `user_progress`, `challenges`).
    * **(IMPORTANT):** This script assumes your `challenges` table definition is included or already exists. You need a separate process or script to populate the `challenges` table with actual CTF data (code snippets, solutions, CWEs, etc.). The application will not function without challenges in the database. The challenge data can be derived from sources like the [MegaVul dataset](https://github.com/Icyrockton/MegaVul).
    ```bash
    python init_db.py
    ```

5.  **Configure Environment Variables (Optional but Recommended):**
    * The application uses a `SECRET_KEY` for session security. While it generates one randomly if not set, it's best practice to set a persistent, strong secret key for development and especially production. You can set this as an environment variable:
        ```bash
        # Linux/macOS
        export SECRET_KEY='your_super_secret_and_random_key_here'

        # Windows (Command Prompt)
        set SECRET_KEY=your_super_secret_and_random_key_here

        # Windows (PowerShell)
        $env:SECRET_KEY='your_super_secret_and_random_key_here'
        ```
    * Consider using a `.env` file and a library like `python-dotenv` for easier management in development.

6.  **Run the Flask Development Server:**
    ```bash
    flask run
    # OR (if __main__ block is set up as in your app.py)
    python app.py
    ```
    The application should now be accessible at `http://127.0.0.1:5000` (or the specified host/port).

## Database Schema

The application uses an SQLite database (`auditor_challenges.db`) with the following main tables:

* **`users`**: Stores user information.
    * `id` (INTEGER, PK, AI): Unique user ID.
    * `username` (TEXT, UNIQUE, NOT NULL): User's chosen name.
    * `password_hash` (TEXT, NOT NULL): Securely hashed password.
    * `created_at` (TIMESTAMP): When the user registered.
* **`user_progress`**: Tracks individual user progress.
    * `user_id` (INTEGER, PK, FK -> users.id): Links to the user.
    * `total_score` (INTEGER): User's current score.
    * `completed_count` (INTEGER): Number of challenges correctly solved.
    * `seen_challenges` (TEXT): JSON string list of challenge IDs the user has been assigned.
* **`challenges`**: Stores the CTF challenge data (derived from sources like MegaVul).
    * `id` (INTEGER, PK): Unique challenge ID.
    * `title` (TEXT): Title of the challenge.
    * `vulnerable_code` (TEXT): The code snippet with the vulnerability.
    * `fixed_code` (TEXT): The corrected version of the code (for diff view).
    * `difficulty` (TEXT): e.g., 'easy', 'medium', 'hard', 'insane'.
    * `cwe_id` (TEXT): The primary CWE associated with the vulnerability (e.g., 'CWE-120').
    * `cwe_name` (TEXT): A descriptive name for the CWE.
    * `cve_id` (TEXT, Optional): Associated CVE identifier, if applicable.
    * `solution` (TEXT): Explanation of the vulnerability and fix.
    * *(Potentially other fields like `hint` if re-added)*

**Note:** Populating the `challenges` table is a prerequisite for using the application. You will need to add your own challenge data or use a script to import it, potentially processing data from the [MegaVul dataset](https://github.com/Icyrockton/MegaVul).

## Usage

1.  Navigate to the application URL (e.g., `http://127.0.0.1:5000`).
2.  Register a new account or Log In via the "My Account" dropdown.
3.  Go to the "Challenges" page (`/ctf`).
4.  Select a difficulty level using the dropdown.
5.  A challenge will load. Analyze the source code.
6.  Optionally, use the "Show Diff View" button to compare with a fixed version (incurs a score penalty).
7.  Select the CWE you believe is present in the code from the radio buttons.
8.  Click "Submit Assessment".
9.  View the results, explanation, and your updated score.
10. Use the "Load Next Challenge" button (on the results page) or the "New Challenge" button (next to the difficulty dropdown) to get a new challenge.
11. Check your progress on the "Profile" page and see rankings on the "Scoreboard" (both accessible from the "My Account" dropdown).

## Deployment (Conceptual)

For production deployment, do **not** use the built-in Flask development server (`flask run` or `app.run(debug=True)`). Instead, use a production-ready setup:

1.  **WSGI Server:** Use Gunicorn or Waitress to run the Flask application.
    ```bash
    # Example using Gunicorn
    gunicorn --workers 4 --bind 127.0.0.1:5000 app:app
    ```
2.  **Reverse Proxy:** Place a web server like Nginx or Apache in front of the WSGI server. Nginx/Apache will handle incoming public requests, serve static files directly, manage HTTPS (SSL/TLS termination), and forward dynamic requests to Gunicorn/Waitress.
3.  **Process Management:** Use `systemd` or `supervisor` to manage the Gunicorn/Waitress process (start on boot, restart on failure).
4.  **HTTPS:** Obtain and configure an SSL/TLS certificate (Let's Encrypt via `certbot` is recommended) on the reverse proxy (Nginx/Apache).
5.  **Environment Variables:** Set `SECRET_KEY` and any other configuration securely as environment variables on the server.

*(See specific tutorials for deploying Flask with Gunicorn/Nginx/systemd on your chosen server OS).*

## Acknowledgements

* The challenge dataset used in this project is based on the [MegaVul dataset](https://github.com/Icyrockton/MegaVul) created by Icyrockton.

## Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for bugs, feature requests, or improvements.
## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details. *(Optional: Create a LICENSE.md file with the MIT license text)*
z
