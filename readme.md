# 🏠 Rental Home Management System (RHMS)

**RHMS** is a robust, Django-based **Property Management ERP** designed to bridge the gap between landlords, tenants, and maintenance staff. From tracking **payments** to managing **repair tickets**, RHMS centralizes the entire rental lifecycle into a single, intuitive interface.

---

## 🚀 Key Features

- **Triple-Role System**  
  Custom dashboards tailored for **Landlords** (analytics & oversight), **Tenants** (payments & issues), and **Maintenance Staff** (task tracking).

- **Smart Authentication**  
  Dual-identifier login (Username or Email) with a built-in **Security Guard** that forces tenants to update temporary passwords upon first login.

- **Financial Integrity**  
  An automated balance engine that recalculates tenant debt instantly whenever payments are confirmed, edited, or deleted.

- **Interactive Analytics**  
  Real-time data visualization using **Chart.js** to track revenue trends and maintenance distribution.

- **One-Click Compliance**  
  Exportable **CSV reports** for revenue summaries, tenant arrears, and maintenance history.

---

## 🛠️ Tech Stack

- **Backend:** Python 3.10+ / Django 6.0  
- **Database:** SQLite (Development) / PostgreSQL (Production-ready)  
- **UI/UX:** HTML5, Vanilla JavaScript, CSS3 (custom variables), Bootstrap 5 via Crispy Forms  
- **Charts:** Chart.js  

---

## 🛠️ Step 1: Prerequisites

Ensure the following are installed:

- Python 3.10+
- pip
- Git

---

## 💻 Step 2: Installation & Setup

### 1. Clone & Enter the Project

    git clone <your-repository-link>
    cd RHMS

### 2. Set Up a Virtual Environment

**macOS / Linux**

    python3 -m venv venv
    source venv/bin/activate

**Windows**

    python -m venv venv
    venv\Scripts\activate

### 3. Install Dependencies

    pip install -r requirements.txt

---

## 🗄️ Step 3: Database & Superuser Initialization

> **Important:** RHMS uses a **Custom User Model**. The order below is critical.

### 1. Generate & Apply Migrations

    python manage.py makemigrations accounts
    python manage.py migrate

### 2. Create the Master Admin (Landlord)

    python manage.py createsuperuser

Follow the prompts to set your username, email, and password.

### 3. Assign the Landlord Role

    python manage.py runserver

Open your browser and go to:

    http://127.0.0.1:8000/admin

- Log in with your superuser account  
- Under **Users**, locate your account  
- Change **Role** to **Landlord**  
- Click **Save**

---

## 🛡️ Step 4: Security & Validation

### Password Strength

Enable strong password validation in `renthouse/settings.py`:

    AUTH_PASSWORD_VALIDATORS = [
        { 'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator', },
        { 'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', },
        { 'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator', },
        { 'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator', },
    ]

---

## 🔑 Step 5: User Workflows

### 🏢 For Landlords (Manager)

- Dashboard:  
      
      http://127.0.0.1:8000/

- Add properties, units, and rent targets  
- Approve or manually onboard tenants  
- Confirm tenant payments to auto-update balances  

### 🏠 For Tenants (Resident)

- Self-register and wait for landlord approval  
- Change password on first login  
- Report maintenance issues  
- Submit formal move-out notices  

### 🛠️ For Maintenance Staff (Technician)

- Register and select a **Target Landlord**  
- View assigned tasks  
- Update task status: Assigned → In Progress → Completed  

---

## 📁 Project Structure

    renthouse/      # Core project configuration
    accounts/       # Core application logic
     ├── models.py  # Users, properties, tenants, payments
     ├── views.py   # Business logic and role handling
     ├── forms.py   # Styled Django ModelForms
    templates/      # HTML templates
    static/         # styles.css and main.js

---

## 🔍 Pro-Tip: Database Inspection

RHMS uses SQLite by default.

**Ubuntu**

    sudo apt install sqlitebrowser

**Windows / macOS**

    https://sqlitebrowser.org