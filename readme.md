🏠 Rental Home Management System (RHMS)
A robust, Django-based Property Management ERP designed to bridge the gap between landlords, tenants, and maintenance staff. From tracking M-Pesa payments to managing repair tickets, RHMS centralizes the entire rental lifecycle.

🚀 Key Features
Triple-Role System: Custom dashboards for Landlords (Analytics), Tenants (Payments/Issues), and Maintenance Staff (Task Tracking).

Smart Authentication: Dual-identifier login (Username or Email) with a Security Guard that forces tenants to change temporary passwords upon first login.

Financial Integrity: Automated balance engine that recalculates tenant debt instantly when payments are confirmed, edited, or deleted.

Interactive Analytics: Real-time data visualization using Chart.js for revenue trends and maintenance distribution.

One-Click Compliance: Exportable CSV reports for revenue, arrears, and maintenance history.

🛠️ Tech Stack
Backend: Python / Django 6.0

Database: SQLite (Development) / PostgreSQL (Production Ready)

UI/UX: HTML5, Vanilla JavaScript, CSS3 (Custom variables), Bootstrap 5 via Crispy Forms.

Charts: Chart.js for revenue and maintenance analytics.

🛠️ Step 1: Prerequisites
Ensure you have the following installed:

Python 3.10+

pip (Python Package Manager)

Git

💻 Step 2: Installation & Setup
1. Clone & Enter the Project
Bash
git clone <your-repository-link>
cd RHMS
1. Set Up a Virtual Environment
macOS/Linux:

Bash
python3 -m venv venv
source venv/activate
Windows:

Bash
python -m venv venv
venv\Scripts\activate
3. Install Dependencies
Bash
pip install -r requirements.txt
🗄️ Step 3: Database & Superuser
Since RHMS uses a Custom User Model, the order of migrations is crucial.

Bash
# 1. Create migration files
python manage.py makemigrations accounts

# 2. Apply migrations to the database
python manage.py migrate

# 3. Create your Master Admin (Landlord)
First, create a Superuser (Master Admin):

python manage.py createsuperuser

Follow the prompts to set your username, email, and password.

Assign the Landlord Role

Run the server:

python manage.py runserver

Go to:

http://127.0.0.1:8000/admin

Log in with your superuser account.

Under Users, find your account.

Change the Role dropdown to landlord.

Click Save.

🛡️ Step 4: Security & Validation (Test Mode vs Pro)
1. Password Strength

Find AUTH_PASSWORD_VALIDATORS in renthouse/settings.py. Uncomment the lines inside the list (remove the #) to prevent users from picking weak passwords like 12345.

AUTH_PASSWORD_VALIDATORS = [
    { 'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator', },
    { 'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', },
    { 'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator', },
    { 'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator', },
]

🔑 Step 5 User Workflows (How to use RHMS)
🏢 For Landlords (The Manager)
Login: Access the dashboard at http://127.0.0.1:8000/.

Add Property: Navigate to Properties and add your first building.

Onboard Tenants: You can manually add a tenant (their phone number becomes their temporary password) or approve "Pending" signups from the Tenants page.

Verify Payments: When tenants report payments, review them in the Payments tab and click Confirm to automatically deduct the amount from their balance.

🏠 For Tenants (The Resident)
Self-Registration: Tenants can sign up and select their building/unit. They remain "Pending" until the landlord approves them.

First Login: If added by a landlord, the tenant logs in with their phone number and is immediately prompted to set a private password.

Report Issues: Tenants can submit maintenance requests with a description of the problem.

Move-Out Notice: Tenants can initiate a formal "Notice to Vacate" through their dashboard.

🛠️ For Maintenance Staff (The Technician)
Application: Staff sign up and select a "Target Landlord" to work for.

Task Management: Once approved by the landlord in Manage Staff, technicians receive assigned tasks.

Status Updates: Technicians can update tasks from "Assigned" to "In Progress" or "Completed."

📁 Project Structure
renthouse/: Core project settings and URL routing.

accounts/: The heart of the app.

models.py: Defines the relationship between Landlords, Properties, Tenants, and Payments.

views.py: Contains the logic for financial calculations and role-based redirects.

forms.py: Django ModelForms styled with CSS variables for theme support.

templates/: HTML structures with specific folders for maintenance and tenants.

static/: Unified styles.css and main.js handling the Dark Mode engine.

🔍 Pro-Tip: Database Inspection

Since the system runs on SQLite, you can view the raw tables directly using DB Browser for SQLite.

Installation

Ubuntu

sudo apt install sqlitebrowser

Windows/macOS
Download from: https://sqlitebrowser.org