# 🚀 AI Career Guidance & Analytics Platform

An intelligent, full-stack career guidance and assessment platform powered by Machine Learning, Natural Language Processing, and Flask.

---

## ✨ Features

- **🤖 ML-Powered Career Recommendation**: Predicts top career paths based on user skills, interests, and academic performance with match probability scoring.
- **📄 ATS Resume Analyzer**: Parses PDF/DOCX resumes, calculates ATS match score, extracts detected skills, highlights missing competencies, and gives targeted improvement suggestions.
- **📊 Interactive Skill Gap & Insights**: Real-time salary insights, learning roadmaps, curated resources, and portfolio project ideas.
- **🔐 User Authentication System**: Individual user registration, password hashing (`werkzeug.security`), secure session management, and personal profile tracking.
- **👑 Advanced Admin Panel (`/admin`)**:
  - **Analytics Dashboard**: Real-time KPI metrics, prediction breakdown charts (Chart.js), user activity feeds.
  - **User Management**: View, edit roles (`admin`/`user`), reset passwords, and manage accounts.
  - **Career Track Editor**: Dynamically add, update, or remove career tracks, salary packages, and roadmaps in real time.
  - **Assessment Logs**: Search, review, and moderate prediction history.

---

## 🛠️ Tech Stack

- **Backend**: Python 3, Flask, Werkzeug, Gunicorn
- **Machine Learning**: Scikit-learn (RandomForestClassifier / TF-IDF), NumPy, Joblib
- **Document Parsing**: PyPDF, python-docx
- **Database**: SQLite3 (`career_history.db`)
- **Frontend**: HTML5, Tailwind CSS, Bootstrap 5, FontAwesome, Chart.js
- **Deployment**: Render Cloud (Web Service / Blueprint), GitHub CI/CD

---

## 🚀 Quick Start Guide (Local)

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. (Optional) Retrain ML Model
```bash
python train_model.py
```

### 3. Run the Application
```bash
python app.py
```
Open **`http://127.0.0.1:5000`** in your browser.

---

## ☁️ Deploying on Render (Free Cloud Hosting)

This repository includes pre-configured **`render.yaml`**, **`Procfile`**, and **`runtime.txt`** for seamless Render deployment.

### Option A: 1-Click / Blueprint Deployment
1. Log in to your [Render Dashboard](https://dashboard.render.com/).
2. Click **New +** -> **Blueprint**.
3. Connect your GitHub repository (`the-life-passenger/AI-Career-Guidance`).
4. Render will automatically detect `render.yaml` and configure the web service with free tier settings.
5. Click **Apply**.

### Option B: Manual Web Service Setup
1. On [Render Dashboard](https://dashboard.render.com/), click **New +** -> **Web Service**.
2. Select your repository: `the-life-passenger/AI-Career-Guidance`.
3. Configure settings:
   - **Environment**: `Python 3`
   - **Region**: Any (e.g. `Singapore` or `Oregon`)
   - **Branch**: `main`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
   - **Instance Type**: `Free`
4. Add Environment Variable:
   - `PYTHON_VERSION`: `3.11.9`
5. Click **Create Web Service**. Your app will be live with a free `https://<service-name>.onrender.com` URL!

---

## 🔑 Default Login Credentials

| Role | Email | Password | Access |
| :--- | :--- | :--- | :--- |
| **Admin** | `admin@careerai.com` | `admin123` | Full access to `/admin`, Analytics, Users & Careers CRUD |
| **Demo User** | `priya.tiwari050706@gmail.com` | `password123` | Personal profile (`/profile`), Assessments & History |

*(Note: One-click demo login buttons are also provided on the `/login` screen)*

---

## 📁 Project Structure

```
AI_Career_Guidance/
├── app.py                  # Main Flask application & API routes
├── train_model.py          # Machine learning model training script
├── career_model.pkl        # Trained ML model & vectorizer
├── career_history.db       # SQLite database (Users, Careers, History)
├── requirements.txt        # Python package dependencies (Flask, Gunicorn, Scikit-learn, etc.)
├── Procfile                # WSGI command for cloud hosting (gunicorn app:app)
├── render.yaml             # Render Blueprint configuration
├── runtime.txt             # Python runtime specification (python-3.11.9)
├── .gitignore              # Ignored files (virtualenvs, cache, json dumps)
├── templates/              # Jinja2 HTML templates
│   ├── base.html           # Main navigation & layout
│   ├── index.html          # Landing page
│   ├── login.html          # Authentication login
│   ├── register.html       # User registration
│   ├── profile.html        # Personal user profile
│   ├── assessment.html     # Skills assessment form
│   ├── result.html         # ML prediction results
│   ├── resume_analyzer.html# ATS Resume upload & analysis
│   ├── skill_gap.html      # Skill gap & learning roadmap
│   ├── career_insights.html# Salary trends & career explorer
│   └── admin/              # Dedicated Admin Control Center
│       ├── base_admin.html
│       ├── dashboard.html
│       ├── users.html
│       ├── user_edit.html
│       ├── careers.html
│       ├── career_form.html
│       └── history.html
└── uploads/                # Temporary upload folder for resumes
```
