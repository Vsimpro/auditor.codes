# Code Auditor CTF - Setup & Deployment Guide

This guide will walk you through setting up the Code Auditor CTF application for local development and deploying it on an Ubuntu server.

## Prerequisites (General)

* Git
* Python 3 (3.8 or newer recommended)
* `pip` (Python package installer)
* `python3-venv` (for creating virtual environments)

## Local Development Setup

Follow these steps to get the application running on your local machine.

### 1. Clone the Repository
```bash
git clone [https://github.com/your-username/code-auditor-ctf.git](https://github.com/your-username/code-auditor-ctf.git) auditor.codes
cd auditor.codes
```
*(Replace `https://github.com/your-username/code-auditor-ctf.git` with your actual repository URL)*

### 2. Create and Activate Virtual Environment
It's highly recommended to use a virtual environment to manage project dependencies.
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows, use: venv\Scripts\activate
```
Your terminal prompt should now be prefixed with `(venv)`.

### 3. Install Dependencies
Install the required Python packages listed in `requirements.txt`:
```bash
pip install -r requirements.txt
```

### 4. Initialize the Database
The application uses SQLite. The `conf/converter_db.py` script initializes the database schema and populates challenges.
```bash
python conf/converter_db.py
```
This will create an `auditor_challenges.db` file in the root project directory.

### 5. Configure Environment Variables
Your application requires a `FLASK_SECRET_KEY`.
* **Generate a Secret Key:**
    ```bash
    python -c "import secrets; print(secrets.token_hex(32))"
    ```
    Copy the generated key.
* **Set the Environment Variable:**
    You can set this in your terminal for the current session:
    ```bash
    export FLASK_SECRET_KEY="your_generated_secret_key_here"
    ```
    Alternatively, for more persistent local development, you can use a `.env` file and the `python-dotenv` library (install with `pip install python-dotenv` and add to `requirements.txt`). Then, create a `.env` file in the project root (`/var/www/auditor.codes/`):
    ```
    FLASK_SECRET_KEY="your_generated_secret_key_here"
    ```
    Your `app.py` has been updated to load `FLASK_SECRET_KEY`.

### 6. Run the Flask Development Server
With the virtual environment active and `FLASK_SECRET_KEY` set:
```bash
flask run
# Or, if your app.py has `if __name__ == '__main__': app.run(...)`:
# python app.py
```
The application should now be running, typically at `http://127.0.0.1:5000/`.

## Server Deployment (Ubuntu)

This section details deploying the application on an Ubuntu server (tested on 24.04) using Gunicorn and Nginx.

### Prerequisites (Server)

* Ubuntu server.
* A domain name pointing to your server's IP address (optional, but recommended for HTTPS).
* Basic knowledge of the Linux command line.
* Root or `sudo` access on your server.

### Step 1: Prepare Server Environment
Update your system and install required system packages:
```bash
sudo apt update
sudo apt upgrade -y
sudo apt install -y python3 python3-pip python3-venv nginx sqlite3
```

### Step 2: Set Up Application Code
Clone your repository to the server (e.g., in `/var/www/`).
```bash
sudo mkdir -p /var/www/
cd /var/www/
# Replace with your actual Git repository URL
sudo git clone [https://github.com/your-username/code-auditor-ctf.git](https://github.com/your-username/code-auditor-ctf.git) auditor.codes
# Set appropriate ownership (replace 'your_deploy_user' with the user who will run the app)
sudo chown -R your_deploy_user:your_deploy_user /var/www/auditor.codes
cd /var/www/auditor.codes
```
*(For the rest of this guide, we'll assume `your_deploy_user` is `s0urc3` as used in previous examples, adjust if different)*

### Step 3: Set Up Python Virtual Environment & Dependencies
As user `your_deploy_user` (e.g., `s0urc3`):
```bash
# Ensure you are in the project directory
# cd /var/www/auditor.codes

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install gunicorn  # Gunicorn will be used as the production WSGI server
deactivate # Optional, systemd service will use absolute paths
```

### Step 4: Initialize the Database
As user `your_deploy_user` (e.g., `s0urc3`), from the project directory `/var/www/auditor.codes/` and with the venv active:
```bash
source venv/bin/activate
python conf/converter_db.py
deactivate
```
Ensure `auditor_challenges.db` is created and owned by `your_deploy_user`.

### Step 5: Configure Gunicorn `systemd` Service
Create a `systemd` service file to manage the Gunicorn process.

1.  **Create the service file:**
    ```bash
    sudo nano /etc/systemd/system/auditor-ctf.service
    ```

2.  **Add the following content:**
    Replace `your_deploy_user` with the actual username (e.g., `s0urc3`).
    Generate a strong, unique secret key.
    ```ini
    [Unit]
    Description=Gunicorn instance to serve Code Auditor CTF
    After=network.target

    [Service]
    User=your_deploy_user
    Group=your_deploy_user
    WorkingDirectory=/var/www/auditor.codes
    Environment="PATH=/var/www/auditor.codes/venv/bin:%{ENV:PATH}"
    Environment="FLASK_SECRET_KEY=place_your_strong_random_secret_key_here"
    ExecStart=/var/www/auditor.codes/venv/bin/python -m gunicorn.app.wsgiapp --workers 3 --bind 127.0.0.1:5000 app:app
    Restart=always

    [Install]
    WantedBy=multi-user.target
    ```
    * **`User` & `Group`**: Set to the user that owns the application files (e.g., `s0urc3`).
    * **`WorkingDirectory`**: Path to your project root.
    * **`Environment="PATH=..."`**: Prepends the venv's bin directory to the system PATH.
    * **`Environment="FLASK_SECRET_KEY=..."`**: **Crucial!** Set a strong, unique secret key. Generate one with `python3 -c "import secrets; print(secrets.token_hex(32))"`. Your `app.py` must be configured to read this *exact* environment variable name.
    * **`ExecStart`**: This is the command to start Gunicorn.
        * It uses the Python interpreter from your virtual environment.
        * `--workers 3`: Adjust the number of worker processes based on your server's CPU cores (a common starting point is `2 * num_cores + 1`).
        * `app:app`: Assumes your Flask application instance is named `app` in `app.py`.

3.  **Enable and Start the Service:**
    ```bash
    sudo systemctl daemon-reload
    sudo systemctl start auditor-ctf
    sudo systemctl enable auditor-ctf  # To start on boot
    sudo systemctl status auditor-ctf  # Verify it's running
    ```

### Step 6: Configure Nginx as a Reverse Proxy
Nginx will act as a reverse proxy, handling incoming HTTP(S) requests and forwarding them to Gunicorn.

1.  **Create an Nginx configuration file:**
    ```bash
    sudo nano /etc/nginx/sites-available/auditor.codes
    ```

2.  **Add the following configuration:**
    Replace `auditor.codes www.auditor.codes` with your domain name or `localhost` if testing locally with Nginx.
    ```nginx
    server {
        listen 80;
        server_name auditor.codes www.auditor.codes; # Or your server's IP / localhost

        location / {
            proxy_pass [http://127.0.0.1:5000](http://127.0.0.1:5000); # Gunicorn's address
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_redirect off;
            proxy_buffering off; # Useful for SSE or long polling if ever used
        }

        location /static {
            alias /var/www/auditor.codes/static; # Serve static files directly
            expires 7d; # Add caching for static assets
            access_log off;
        }
    }
    ```

3.  **Enable the Site and Test Nginx:**
    ```bash
    sudo ln -s /etc/nginx/sites-available/auditor.codes /etc/nginx/sites-enabled/
    # Optional: Remove default Nginx site if it conflicts
    # sudo rm /etc/nginx/sites-enabled/default 
    sudo nginx -t # Test Nginx configuration
    sudo systemctl restart nginx
    ```

### Step 7: Set Up HTTPS with Let's Encrypt (Optional, Recommended for Production)
If you have a domain name:
```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d auditor.codes -d www.auditor.codes # Replace with your domain(s)
```
Follow the prompts. Certbot will obtain SSL certificates and automatically update your Nginx configuration for HTTPS.

## Troubleshooting

### Gunicorn Service (`auditor-ctf.service`) Won't Start or Fails
1.  **Check Status:** `sudo systemctl status auditor-ctf.service`
2.  **Detailed Logs:** `sudo journalctl -xeu auditor-ctf.service --no-pager --full`
    * **`203/EXEC` errors:** Usually means the path in `ExecStart` is wrong, the file doesn't exist, or the `User` doesn't have execute permission on the executable (`.../venv/bin/python`) or its path components. Ensure the `venv` exists and paths are correct.
    * **Gunicorn exit codes (e.g., status=1, status=3):**
        * `status=3` (Worker failed to boot): Often means Gunicorn couldn't load `app:app`. This can be due to `ImportError`s in your `app.py` (missing dependencies in the venv) or `app.py` not being in the `WorkingDirectory`. Test the `ExecStart` command manually as the specified `User` from the `WorkingDirectory` (see "Manually Test Gunicorn" below).
    * **Python Tracebacks:** These indicate errors within your Flask application code.

3.  **Manually Test Gunicorn (as the service user):**
    This is crucial for diagnosing issues with Gunicorn loading your app.
    ```bash
    sudo -u your_deploy_user -s  # e.g., sudo -u s0urc3 -s
    cd /var/www/auditor.codes   # The WorkingDirectory
    # Set environment variables from the service file
    export FLASK_SECRET_KEY="your_actual_secret_key_from_service_file"
    export PATH="/var/www/auditor.codes/venv/bin:$PATH" 
    # Run the Gunicorn command from ExecStart
    /var/www/auditor.codes/venv/bin/python -m gunicorn.app.wsgiapp --workers 3 --bind 127.0.0.1:5000 app:app
    # Look for errors. Press Ctrl+C to stop.
    exit # Exit the user's shell
    ```

### Nginx Errors (e.g., 502 Bad Gateway, Connection Refused)
* **Check Nginx error log:** `sudo tail -n 50 /var/log/nginx/error.log`
* **"Connection refused"**: Usually means Gunicorn service (`auditor-ctf`) is not running or not listening on `127.0.0.1:5000`. Ensure `auditor-ctf.service` is active and running.
* **502 Bad Gateway**: Gunicorn might be running but crashing when Nginx tries to connect, or there's a proxy configuration issue. Check both Gunicorn logs (via `journalctl`) and Nginx logs.

### Application Errors (e.g., Database, Login)
* **Check Gunicorn logs:** `sudo journalctl -fu auditor-ctf.service` for live Flask application errors.
* **Database Permissions:** Ensure the `User` running Gunicorn (e.g., `s0urc3`) has read *and* write permissions to `auditor_challenges.db` and the directory `/var/www/auditor.codes/` (for SQLite journal files).
    ```bash
    ls -l /var/www/auditor.codes/auditor_challenges.db
    # Should be owned by your_deploy_user:your_deploy_user
    ```
* **`SECRET_KEY` Consistency:** Unexpected logouts are often due to the `FLASK_SECRET_KEY` not being consistently applied across Gunicorn workers. Ensure it's correctly set in the `systemd` service file and correctly read by `app.py` using `os.environ.get('FLASK_SECRET_KEY')`.

### Nginx Shows Default Page
Ensure you've enabled your site's Nginx configuration and disabled/removed the default Nginx site if it conflicts:
```bash
sudo ln -sfn /etc/nginx/sites-available/auditor.codes /etc/nginx/sites-enabled/auditor.codes
# sudo rm -f /etc/nginx/sites-enabled/default # If it exists and causes issues
sudo systemctl restart nginx
```

## Maintenance

### Updating the Application
```bash
cd /var/www/auditor.codes
sudo -u your_deploy_user git pull # Or however you update your code
# Activate venv as your_deploy_user to update dependencies
sudo -u your_deploy_user /var/www/auditor.codes/venv/bin/pip install -r requirements.txt
# Restart the service
sudo systemctl restart auditor-ctf
```

### Certificate Renewal (Let's Encrypt)
Certbot usually sets up an automatic renewal. You can test renewal with:
```bash
sudo certbot renew --dry-run
```

## Further Customization

* Configure firewall (UFW) to allow only ports 80 (HTTP) and 443 (HTTPS).
* Set up regular database backups.
* Implement more advanced rate limiting (e.g., in Nginx, or Flask-Limiter with Redis).
* Nginx performance tuning (caching, compression).

## Support

If you encounter any issues with deployment, please open an issue on the GitHub repository.

---

Happy coding and security auditing!
