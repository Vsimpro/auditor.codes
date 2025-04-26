# Code Auditor CTF - Deployment Guide

This guide will walk you through the process of deploying the Code Auditor CTF application on a Ubuntu server.

## Prerequisites

- Ubuntu server (tested on Ubuntu 24.04)
- A domain name pointing to your server (optional for HTTPS)
- Basic knowledge of Linux command line
- Root or sudo access on your server

## Step 1: Prepare the Environment

First, update your system and install required packages:

```bash
sudo apt update
sudo apt upgrade -y
sudo apt install -y python3 python3-pip python3-venv nginx sqlite3
```

## Step 2: Set Up the Application

### Clone the Repository

```bash
# Create directory in /var/www/
sudo mkdir -p /var/www/
cd /var/www/
sudo git clone https://github.com/your-username/code-auditor-ctf.git auditor.codes
sudo chown -R $USER:$USER /var/www/auditor.codes
```

### Set Up Python Virtual Environment

```bash
cd /var/www/auditor.codes
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install gunicorn  # For production server
```

### Initialize the Database

```bash
python initdb.py
```

## Step 3: Configure Gunicorn Service

Create a systemd service file for Gunicorn:

```bash
sudo nano /etc/systemd/system/auditor-ctf.service
```

Add the following content (replace `your-user` with your system username):

```
[Unit]
Description=Gunicorn instance to serve Code Auditor CTF
After=network.target

[Service]
User=your-user
Group=your-user
WorkingDirectory=/var/www/auditor.codes
Environment="PATH=/var/www/auditor.codes/venv/bin"
Environment="FLASK_SECRET_KEY=your-secret-key-here"
ExecStart=/var/www/auditor.codes/venv/bin/gunicorn --workers 3 --bind 127.0.0.1:5000 app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

Remember to replace `your-secret-key-here` with a secure random string. You can generate one with:

```bash
python -c "import secrets; print(secrets.token_hex(24))"
```

Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl start auditor-ctf
sudo systemctl enable auditor-ctf
sudo systemctl status auditor-ctf  # Verify it's running
```

## Step 4: Configure Nginx as a Reverse Proxy

Create an Nginx configuration file:

```bash
sudo nano /etc/nginx/sites-available/auditor.codes
```

Add the following configuration:

```nginx
server {
    listen 80;
    server_name auditor.codes www.auditor.codes;  # Replace with your domain name or use localhost

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
        proxy_buffering off;
    }

    # Serve static files directly
    location /static/ {
        alias /var/www/auditor.codes/static/;
    }
}
```

Create a symbolic link to enable the site and remove the default site:

```bash
sudo ln -s /etc/nginx/sites-available/auditor.codes /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default  # Remove default site if it exists
```

Test the Nginx configuration and restart:

```bash
sudo nginx -t
sudo systemctl restart nginx
```

## Step 5: Set Up HTTPS with Let's Encrypt (Optional)

If you have a domain name and want to enable HTTPS:

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d auditor.codes -d www.auditor.codes
```

Follow the prompts to complete the setup. Certbot will automatically update your Nginx configuration.

## Troubleshooting

### Service Won't Start

Check the service status and logs:

```bash
sudo systemctl status auditor-ctf
sudo journalctl -u auditor-ctf.service -n 100
```

Common issues:
- Incorrect permissions
- Missing dependencies
- Environment variables not set correctly

### Nginx Shows Default Page

Make sure you've removed the default site:

```bash
sudo rm -f /etc/nginx/sites-enabled/default
sudo systemctl restart nginx
```

### Application Routes Not Working

Check Nginx error log:

```bash
sudo tail -n 50 /var/log/nginx/error.log
```

Verify that your Flask application works directly:

```bash
curl http://127.0.0.1:5000/
```

### HTTPS Not Working

Check your Certbot configuration:

```bash
sudo certbot certificates
```

Make sure your domain is properly pointing to your server's IP address.

## Maintenance

### Updating the Application

```bash
cd /var/www/auditor.codes
sudo git pull
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart auditor-ctf
```

### Certificate Renewal

Let's Encrypt certificates expire after 90 days. Certbot sets up an automatic renewal cron job, but you can test it with:

```bash
sudo certbot renew --dry-run
```

## Further Customization

- Configure firewall settings (UFW) to only allow ports 80 and 443
- Set up database backups
- Implement rate limiting in Nginx
- Configure Nginx for better performance (caching, compression, etc.)

## Support

If you encounter any issues with deployment, please open an issue on the GitHub repository.

---

Happy coding and security auditing!
