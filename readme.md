# Rental Home Management System (RHMS)

A robust, Django-based web application designed for landlords to manage properties, track tenants, record payments (M-Pesa, Cash, Bank), and oversee maintenance requests from a centralized dashboard.

---

## 🚀 Key Features

- **Consolidated Management**  
  Single-app architecture (`accounts`) for easier maintenance and faster performance.

- **Smart Authentication**  
  Support for a dual-identifier login system where users can sign in using either their Username or their Email address.

- **Financial Tracking**  
  Automated balance adjustments that update instantly when payments are recorded, edited, or deleted.

- **Visual Analytics**  
  Interactive charts (via Chart.js) for tracking monthly revenue and maintenance request status.

- **Exportable Reports**  
  One-click CSV downloads for revenue summaries and tenant arrears lists.

- **Dark/Light Mode**  
  User-controlled theme persistence across sessions.

---

## 🛠️ Phase 1: Prerequisites

Before you begin, ensure you have the following installed on your machine:

- **Python 3.10+**  
  The core language used for the backend.

- **pip**  
  The Python package manager.

- **Virtualenv**  
  Recommended for keeping dependencies isolated.

---

## 💻 Phase 2: Installation & Setup (Step-by-Step)

### 1. Clone the Project

Open your terminal and download the repository:

```bash
git clone <your-repository-link>
cd RHMS
2. Set Up a Virtual Environment

On Ubuntu/macOS:

python3 -m venv venv
source venv/activate

On Windows:

python -m venv venv
venv\Scripts\activate
3. Install Dependencies
pip install -r requirements.txt
🗄️ Phase 3: Database Initialization (Crucial)

Since this project uses a custom user model and consolidated structure, you must initialize the database to create the required tables.

# Prepare the database instructions
python manage.py makemigrations accounts

# Build the actual tables
python manage.py migrate
🔑 Phase 4: Accessing the Dashboard
1. Create a Landlord Account

First, create a Superuser (Master Admin):

python manage.py createsuperuser

Follow the prompts to set your username, email, and password.

2. Assign the Landlord Role

Run the server:

python manage.py runserver

Go to:

http://127.0.0.1:8000/admin

Log in with your superuser account.

Under Users, find your account.

Change the Role dropdown to landlord.

Click Save.

🛡️ Phase 5: Security & Validation (Test Mode vs Pro)
1. Password Strength

Find AUTH_PASSWORD_VALIDATORS in renthouse/settings.py. Uncomment the lines inside the list (remove the #) to prevent users from picking weak passwords like 12345.

AUTH_PASSWORD_VALIDATORS = [
    { 'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator', },
    { 'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', },
    { 'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator', },
    { 'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator', },
]
📂 Project Structure
renthouse/        # Project configuration (settings and main URLs)
accounts/         # Core application containing all models, views, and logic
models.py         # Database schema for Users, Properties, Tenants, and Payments
views.py          # Backend logic and data processing
forms.py          # Clean, styled input forms for all data entry
static/           # CSS, JavaScript, and Image assets
templates/        # HTML files for the dashboard and authentication screens
🔍 Pro-Tip: Database Inspection

Since the system runs on SQLite, you can view the raw tables directly using DB Browser for SQLite.

Installation

Ubuntu

sudo apt install sqlitebrowser

Windows/macOS
Download from: https://sqlitebrowser.org