# Extracted Code Snippets - Server Configuration

This document contains code snippets extracted from the Server Code page for project: `{{ project.project_name }}`

---

## 1. SSH Key Management

```bash
# Generate SSH key for {{ project.project_name }}

🔑 1. Generate Project-Specific SSH Key
ssh-keygen -t rsa -b 4096 -f ~/.ssh/{{ project.project_name }}

🔐 2. Start SSH Agent
eval "$(ssh-agent -s)"

➕ 3. Add Your New SSH Key to the Agent
ssh-add ~/.ssh/{{ project.project_name }}

📋 4. Copy the SSH Key to Clipboard
cat ~/.ssh/{{ project.project_name }}.pub

⚙️ 5. Edit the SSH Config File
nano ~/.ssh/config

🏠 6. Add a New Host Configuration
Host {{ project.project_name }}.github.com
    HostName github.com
    User git
    IdentityFile ~/.ssh/{{ project.project_name }}

🔄 7. Clone Your Repository Using the Configured Host
cd /opt
git clone --branch main --single-branch git@{{ project.project_name }}.github.com:{{ project.github_username }}/{{ project.project_name }}.git

🔧 8. Project Setup & Configuration
cd {{ project.project_name }}
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver 0.0.0.0:8000
```

---

## 2. Development Environment Setup

```bash
# Development Environment Setup

🔧 1. Upgrade pip and install dependencies
pip install --upgrade pip
pip install -r requirements.txt
pip install uwsgi

⚙️ 2. Setting up local Django settings
cp examples/local_settings.example {{ project.project_name }}/local_settings.py
nano {{ project.project_name }}/local_settings.py  # Configure your local settings

📁 3. Creating log directory
mkdir -p logs

🚀 4. Testing initial Django run
python manage.py runserver 0.0.0.0:8000
```

---

## 3. Database Setup

```bash
# Database Setup

🗄️ 1. Creating PostgreSQL database
sudo -u postgres psql 
CREATE DATABASE {{ project.database_name }};
\q

🔧 2. Install psycopg2 for Django
pip install psycopg2-binary==2.9.10

⚙️ 3. Database Configuration (add to local_settings.py)
DB_CONFIG = {
    'ENGINE': os.getenv('DB_ENGINE', 'django.db.backends.postgresql'),
    'HOST': os.getenv('DB_HOST', '127.0.0.1'),
    'PORT': os.getenv('DB_PORT', 5432),
    'NAME': os.getenv('DB_NAME', '{{ project.database_name }}'),
    'USER': os.getenv('DB_USER', 'postgres'),
    'PASSWORD': os.getenv('DB_PASS', '<db_password>')
}

🚀 4. Navigate to project and activate environment
cd /opt/{{ project.project_name }}/
source venv/bin/activate

📊 5. Run migrations
python manage.py makemigrations
python manage.py migrate

👤 6. Create superuser
python manage.py createsuperuser

💾 7. Backup database (optional)
pg_dump {{ project.database_name }} > {{ project.database_name }}_backup.sql

# Restore database (if needed)
# psql {{ project.database_name }} < {{ project.database_name }}_backup.sql
```

---

## 4. Production Deployment Setup

```bash
# Production Deployment Setup

📂 1. Setting up uWSGI configuration
mkdir -p uwsgi
cp examples/uwsgi.example uwsgi/uwsgi.ini
cat uwsgi/uwsgi.ini
uwsgi --ini uwsgi/uwsgi.ini

🛠️ 2. Setting up systemd service
sudo cp /opt/{{ project.project_name }}/examples/service.example /etc/systemd/system/{{ project.project_name }}.service
sudo systemctl daemon-reload
sudo systemctl start {{ project.project_name }}.service
sudo systemctl enable {{ project.project_name }}.service
sudo systemctl status {{ project.project_name }}.service

🌐 3. Configuring Nginx
cd /etc/nginx/conf.d/
sudo cp /opt/{{ project.project_name }}/examples/nginx.example {{ project.domain_name }}.conf
sudo nginx -t
sudo systemctl restart nginx

🔁 4. Restarting service
cd /opt/{{ project.project_name }}/
sudo systemctl restart {{ project.project_name }}.service

✅ Deployment setup complete! 🚀
```

---

## 5. Restart Server Commands

**⚠️ Bug Note:** This section contains HTML elements incorrectly embedded inside the `<code>` block (lines 633-636 in source file). The actual clean content should be:

```bash
# Server Restart Commands for {{ project.project_name }}

📂 1. Navigate to Project Directory
cd /opt/{{ project.project_name }}/

📂 2. Activate Virtual Environment
source venv/bin/activate

📂 3. Pull Latest Code
git pull

🔄 4. Restart uWSGI Service
sudo systemctl restart {{ project.project_name }}.service
```

---

## 6. Project Requirements

**⚠️ Bug Note:** The tab ID is misspelled as "Requerment" instead of "Requirement" in the source file.

```bash
# Project Requirements for {{ project.project_name }}

📦 Django Dependencies
Django==4.2.7
pip install uwsgi
🗄️ Database & Storage
pip install psycopg2-binary==2.9.10

-> Obtain SSL Certificate
sudo certbot --nginx
```

---

## Bug Report

### Issue 1: HTML Embedded in Code Block
- **Location:** Restart Server Commands section (lines 633-636)
- **Problem:** HTML div elements are incorrectly placed inside the `<code>` block:
  ```html
  <div class="flex items-center space-x-2 text-green-400">
      <i class="fas fa-sync-alt animate-spin"></i>
      <span>git pull</span>
  </div>
  ```
- **Expected:** Plain text `git pull`
- **Severity:** Medium (breaks code copying functionality)

### Issue 2: Misspelled Tab ID
- **Location:** Project Requirements tab configuration
- **Problem:** Tab ID is "Requerment" instead of "Requirement"
- **Impact:** Confusing for developers maintaining the code
- **Severity:** Low

---

## Download Functionality

### README Download Button

A "Download README" button has been added to the Server Code page that allows users to download a dynamically generated README file for their project.

**Button Location:** Header section of the Server Code page (next to "Back to List" button)

**Access URL:** `projects/<project_id>/download-readme/`

**Features:**
- Downloads a project-specific README.md file
- Includes all code snippets from the Server Code page
- Uses project-specific values (project_name, github_username, domain_name, database_name)
- Requires user authentication and project access permissions

**Implementation:**
- View: `download_readme` in [views.py](file:///d:/Programming/server_dev/Server_dev/DevOps/views.py)
- URL Route: `projects/<int:pk>/download-readme/` in [urls.py](file:///d:/Programming/server_dev/Server_dev/DevOps/urls.py)
- Template: Button added in [server_code.html](file:///d:/Programming/server_dev/Server_dev/DevOps/templates/DevOps/server_code.html)

---

## Source Reference

All code snippets extracted from:
[d:\Programming\server_dev\Server_dev\DevOps\templates\DevOps\server_code.html](file:///d:/Programming/server_dev/Server_dev/DevOps/templates/DevOps/server_code.html)