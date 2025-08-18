Installation
============

Prerequisites
-------------

* Python 3.11 or higher
* PostgreSQL (optional, SQLite is used by default)
* Git

Installation Steps
------------------

1. Clone the repository::

    git clone https://github.com/Tanvir-yzu/Server_dev.git
    cd Server_dev

2. Create a virtual environment::

    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate

3. Install dependencies::

    pip install -r requirements.txt

4. Set up local settings::

    cp examples/local_settings.example Server_dev/local_settings.py
    # Edit the local_settings.py file with your configuration

5. Run migrations::

    python manage.py migrate

6. Create a superuser::

    python manage.py createsuperuser

7. Start the development server::

    python manage.py runserver