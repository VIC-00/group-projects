Rental Home Management System (RHMS)
        A robust, Django-based web application designed for landlords to manage properties, track tenants, record payments (M-Pesa, Cash, Bank), and oversee maintenance requests from a centralized dashboard.

🚀 Features
        Consolidated Management: Single-app architecture (accounts) for easier maintenance.

        Role-Based Access: Specialized views for Landlords (Tenant Portal and Staff Portal planned).

         Financial Tracking: Automated balance adjustments when payments are recorded or edited.

        Visual Analytics: Interactive charts for revenue tracking and maintenance status.

        Dark/Light Mode: User-controlled theme persistence.

        Exportable Reports: One-click CSV downloads for revenue and arrears.

🛠️ Prerequisites
        Before you begin, ensure you have the following installed:

        Python 3.10+

        pip (Python package manager)

        Virtualenv (Recommended)

💻 Installation & Setup
        1. Clone the Project
        Bash
            git clone <your-repository-link>
            cd RHMS
        2. Set Up a Virtual Environment
        On Ubuntu/macOS:

        Bash
            python3 -m venv venv
            source venv/bin/activate
        On Windows:

        Bash
            python -m venv venv
            venv\Scripts\activate
        3. Install Dependencies
        Bash
            pip install django django-crispy-forms crispy-bootstrap5
        4. Database Initialization (Crucial)
        Since this project uses a consolidated model structure, you must initialize the database to create the tables.

        Bash
            python manage.py makemigrations accounts
            python manage.py migrate
        5. Create a Landlord Account
        Create a Superuser:

        Bash
            python manage.py createsuperuser
        Assign Landlord Role:

        Run the server: 

            python manage.py runserver


        Go to http://127.0.0.1:8000/admin

        Under Users, find your account and change the Role to landlord.


        Automatic Dependency Installation:
Instead of installing packages one by one, run:

Bash
    pip install -r requirements.txt


    🔍 Database Inspection (Optional)
        Since the system runs on SQLite, you can view the raw tables, user data, and financial records directly using DB Browser for SQLite.

        What it does: Allows you to open the db.sqlite3 file to see exactly how data is stored in the accounts_customuser, accounts_property, and accounts_payment tables.

        Installation:

        Ubuntu: sudo apt install sqlitebrowser

        Windows/macOS: Download from sqlitebrowser.org


📂 Project Structure
        renthouse/: Project configuration (settings, main URLs).

        accounts/: The core application containing all models, views, and logic.

        models.py: Database schema for Users, Properties, Tenants, and Payments.

        views.py: Backend logic and data processing.

        forms.py: Clean, styled input forms for all data entry.

        static/: CSS, JavaScript, and Image assets.

        templates/: HTML files for the dashboard and authentication.

📝 Important Notes for Beginners
        Migrations: Every time you change models.py, you must run makemigrations and migrate.

        Database: This project uses SQLite3 by default, which is a file named db.sqlite3 in your root folder. Deleting this file resets all data.

        Security: Ensure @login_required decorators are used on all sensitive views to prevent unauthorized access.

🛠️ Built With
        Framework: Django 6.0+

        Frontend: HTML5, CSS3, JavaScript (Vanilla)

        Charts: Chart.js

        Icons: FontAwesome / Emoji-based