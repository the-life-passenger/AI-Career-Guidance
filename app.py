
from flask import Flask, render_template, request, redirect, url_for, session, flash, get_flashed_messages
from functools import wraps
import sqlite3
import os
import time
import json
import re
import uuid
import html
import joblib
from pypdf import PdfReader
from docx import Document
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash


# =========================================================
# FLASK CONFIGURATION
# =========================================================

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "ai-career-guidance-secret-key-3614aeba")

APP_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_FILE = os.path.join(APP_DIR, "career_model.pkl")
DATABASE = os.path.join(APP_DIR, "career_history.db")
UPLOAD_FOLDER = os.path.join(APP_DIR, "uploads")
TEMP_RESULTS_DIR = os.path.join(APP_DIR, "temporary_results")

ALLOWED_EXTENSIONS = {"pdf", "docx"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(TEMP_RESULTS_DIR, exist_ok=True)


# =========================================================
# TEMPORARY RESULT STORAGE & CLEANUP
# =========================================================

def cleanup_temporary_results():
    """Remove temporary JSON result files older than 2 hours to avoid disk bloat."""
    try:
        now = time.time()
        if os.path.exists(TEMP_RESULTS_DIR):
            for filename in os.listdir(TEMP_RESULTS_DIR):
                if filename.endswith(".json"):
                    filepath = os.path.join(TEMP_RESULTS_DIR, filename)
                    if now - os.path.getmtime(filepath) > 7200:
                        try:
                            os.remove(filepath)
                        except OSError:
                            pass
    except Exception as error:
        print("Temporary results cleanup error:", error)


def save_temporary_result(kind, context):
    cleanup_temporary_results()
    token = uuid.uuid4().hex
    path = os.path.join(TEMP_RESULTS_DIR, token + ".json")

    with open(path, "w", encoding="utf-8") as result_file:
        json.dump(
            {"kind": kind, "context": context},
            result_file,
            ensure_ascii=False,
            default=str
        )

    return token


def load_temporary_result(token, expected_kind):
    if not isinstance(token, str) or not re.fullmatch(
        r"[0-9a-f]{32}", token
    ):
        return None

    path = os.path.join(TEMP_RESULTS_DIR, token + ".json")

    if not os.path.isfile(path):
        return None

    try:
        with open(path, "r", encoding="utf-8") as result_file:
            saved = json.load(result_file)

        if saved.get("kind") != expected_kind:
            return None

        context = saved.get("context")

        if not isinstance(context, dict):
            return None

        # Decode HTML entities in saved text before Jinja renders it.
        # Keep normal Jinja autoescaping enabled; do not use |safe.
        def decode_entities(value):
            if isinstance(value, str):
                for _ in range(4):
                    decoded = html.unescape(value)
                    if decoded == value:
                        break
                    value = decoded
                return value

            if isinstance(value, list):
                return [decode_entities(item) for item in value]

            if isinstance(value, tuple):
                return tuple(decode_entities(item) for item in value)

            if isinstance(value, dict):
                return {
                    key: decode_entities(item)
                    for key, item in value.items()
                }

            return value

        return decode_entities(context)

    except (OSError, ValueError, TypeError) as error:
        print("Temporary result loading error:", error)
        return None


# =========================================================
# LOAD MACHINE LEARNING MODEL
# =========================================================

model = None

if os.path.exists(MODEL_FILE):
    try:
        model = joblib.load(MODEL_FILE)
        print("ML model loaded successfully.")
    except Exception as error:
        print("ML model loading error:", error)
else:
    print("Warning: career_model.pkl not found. Rule-based matching will be used.")


# =========================================================
# CAREER DATABASE
# =========================================================

career_data = {
    "Python Developer": {
        "skills": ["Python", "Git", "GitHub", "SQL"],
        "roles": [
            "Python Developer",
            "Backend Developer",
            "Software Developer",
            "Automation Developer"
        ],
        "salary": {
            "entry": "₹3 – ₹6 LPA",
            "experienced": "₹8 – ₹18+ LPA"
        },
        "growth": [
            "Junior Python Developer",
            "Python Developer",
            "Senior Python Developer",
            "Backend / Software Engineer",
            "Technical Lead"
        ],
        "description": (
            "Python Developers create software, backend systems, "
            "automation programs and applications using Python."
        ),
        "reason": (
            "Python is useful for software development, automation, "
            "backend development, AI and data-related work."
        )
    },

    "Java Developer": {
        "skills": ["Java", "SQL", "MySQL", "Git", "GitHub"],
        "roles": [
            "Java Developer",
            "Backend Developer",
            "Software Engineer",
            "Application Developer"
        ],
        "salary": {
            "entry": "₹3 – ₹6 LPA",
            "experienced": "₹8 – ₹20+ LPA"
        },
        "growth": [
            "Junior Java Developer",
            "Java Developer",
            "Senior Java Developer",
            "Software Engineer",
            "Technical Lead"
        ],
        "description": (
            "Java Developers build reliable applications, "
            "backend systems and enterprise software using Java."
        ),
        "reason": (
            "Java is widely used for backend development, "
            "enterprise applications and software engineering."
        )
    },

    "C/C++ Developer": {
        "skills": ["C", "C++", "Git"],
        "roles": [
            "C++ Developer",
            "Software Developer",
            "Systems Programmer",
            "Application Developer"
        ],
        "salary": {
            "entry": "₹3 – ₹6 LPA",
            "experienced": "₹8 – ₹18+ LPA"
        },
        "growth": [
            "Junior Developer",
            "C/C++ Developer",
            "Senior Developer",
            "Software Engineer",
            "Technical Lead"
        ],
        "description": (
            "C and C++ developers work on software, systems "
            "and performance-focused applications."
        ),
        "reason": (
            "C and C++ provide strong programming fundamentals "
            "and are useful for systems and software development."
        )
    },

    "Web Developer": {
        "skills": ["HTML", "CSS", "JavaScript"],
        "roles": [
            "Web Developer",
            "Frontend Developer",
            "Full Stack Developer",
            "UI Developer"
        ],
        "salary": {
            "entry": "₹3 – ₹6 LPA",
            "experienced": "₹8 – ₹18+ LPA"
        },
        "growth": [
            "Junior Web Developer",
            "Web Developer",
            "Senior Web Developer",
            "Full Stack Developer",
            "Technical Lead"
        ],
        "description": (
            "Web Developers create websites and web applications "
            "using frontend and backend technologies."
        ),
        "reason": (
            "HTML, CSS and JavaScript are core technologies "
            "used to build websites and web applications."
        )
    },

    "Frontend Developer": {
        "skills": [
            "HTML", "CSS", "JavaScript", "React", "Angular", "Vue"
        ],
        "roles": [
            "Frontend Developer",
            "UI Developer",
            "React Developer",
            "Web Designer"
        ],
        "salary": {
            "entry": "₹3 – ₹6 LPA",
            "experienced": "₹8 – ₹18+ LPA"
        },
        "growth": [
            "Junior Frontend Developer",
            "Frontend Developer",
            "Senior Frontend Developer",
            "UI Engineer",
            "Frontend Lead"
        ],
        "description": (
            "Frontend Developers build the visible and interactive "
            "part of websites and web applications."
        ),
        "reason": (
            "HTML, CSS, JavaScript and frontend frameworks "
            "directly match this career."
        )
    },

    "Full Stack Developer": {
        "skills": [
            "HTML", "CSS", "JavaScript", "React",
            "Node.js", "SQL", "MySQL", "Git"
        ],
        "roles": [
            "Full Stack Developer",
            "Web Developer",
            "Frontend Developer",
            "Backend Developer"
        ],
        "salary": {
            "entry": "₹4 – ₹7 LPA",
            "experienced": "₹10 – ₹22+ LPA"
        },
        "growth": [
            "Junior Full Stack Developer",
            "Full Stack Developer",
            "Senior Full Stack Developer",
            "Full Stack Engineer",
            "Technical Lead"
        ],
        "description": (
            "Full Stack Developers work on both frontend and "
            "backend parts of web applications."
        ),
        "reason": (
            "Knowledge of frontend, backend and databases "
            "provides a strong match for full stack development."
        )
    },

    "Data Analyst": {
        "skills": [
            "Python", "R", "SQL", "MySQL", "Excel",
            "Power BI", "Tableau", "Pandas", "NumPy"
        ],
        "roles": [
            "Data Analyst",
            "Business Analyst",
            "BI Analyst",
            "Reporting Analyst"
        ],
        "salary": {
            "entry": "₹3 – ₹6 LPA",
            "experienced": "₹8 – ₹18+ LPA"
        },
        "growth": [
            "Junior Data Analyst",
            "Data Analyst",
            "Senior Data Analyst",
            "Business Intelligence Analyst",
            "Data Analytics Lead"
        ],
        "description": (
            "Data Analysts study data and create useful insights, "
            "reports and visualizations for decision making."
        ),
        "reason": (
            "Python, SQL, Excel, Power BI, Tableau and data libraries "
            "are important skills for data analysis."
        )
    },

    "Data Scientist": {
        "skills": ["Python", "R", "SQL", "Pandas", "NumPy"],
        "roles": [
            "Data Scientist",
            "Machine Learning Engineer",
            "Data Analyst",
            "AI Engineer"
        ],
        "salary": {
            "entry": "₹5 – ₹10 LPA",
            "experienced": "₹12 – ₹30+ LPA"
        },
        "growth": [
            "Data Analyst / Junior Data Scientist",
            "Data Scientist",
            "Senior Data Scientist",
            "Lead Data Scientist",
            "AI / Data Science Manager"
        ],
        "description": (
            "Data Scientists use programming, statistics and "
            "machine learning to find patterns and make predictions."
        ),
        "reason": (
            "Python, R, Pandas and NumPy are commonly used in data science."
        )
    },

    "Database Developer": {
        "skills": [
            "SQL", "MySQL", "MongoDB", "PostgreSQL", "Oracle"
        ],
        "roles": [
            "Database Developer",
            "SQL Developer",
            "Database Administrator",
            "Data Engineer"
        ],
        "salary": {
            "entry": "₹3 – ₹6 LPA",
            "experienced": "₹8 – ₹20+ LPA"
        },
        "growth": [
            "Junior Database Developer",
            "Database Developer",
            "Senior Database Developer",
            "Database Engineer",
            "Database Architect"
        ],
        "description": (
            "Database professionals manage, design and maintain "
            "systems used to store and retrieve data."
        ),
        "reason": (
            "SQL and database technologies directly match "
            "database-related careers."
        )
    },

    "DevOps Engineer": {
        "skills": ["Git", "GitHub", "Linux", "Networking"],
        "roles": [
            "DevOps Engineer",
            "Cloud Engineer",
            "Site Reliability Engineer",
            "Release Engineer"
        ],
        "salary": {
            "entry": "₹4 – ₹8 LPA",
            "experienced": "₹10 – ₹25+ LPA"
        },
        "growth": [
            "Junior DevOps Engineer",
            "DevOps Engineer",
            "Senior DevOps Engineer",
            "DevOps Lead",
            "Cloud / Platform Architect"
        ],
        "description": (
            "DevOps Engineers help automate software development, "
            "deployment and infrastructure processes."
        ),
        "reason": (
            "Git, GitHub, Linux and networking are useful foundations for DevOps."
        )
    },

    "UI/UX Designer": {
        "skills": ["Figma", "Photoshop"],
        "roles": [
            "UI Designer",
            "UX Designer",
            "Product Designer",
            "Visual Designer"
        ],
        "salary": {
            "entry": "₹3 – ₹6 LPA",
            "experienced": "₹8 – ₹18+ LPA"
        },
        "growth": [
            "Junior UI/UX Designer",
            "UI/UX Designer",
            "Senior Product Designer",
            "Lead Designer",
            "Design Manager"
        ],
        "description": (
            "UI/UX Designers create user-friendly interfaces "
            "and improve the overall experience of digital products."
        ),
        "reason": (
            "Figma and Photoshop are useful tools for interface "
            "and visual design."
        )
    },

    "Software Developer": {
        "skills": ["Python", "Java", "C", "C++", "C#", "Git"],
        "roles": [
            "Software Developer",
            "Software Engineer",
            "Application Developer",
            "System Developer"
        ],
        "salary": {
            "entry": "₹3 – ₹7 LPA",
            "experienced": "₹10 – ₹25+ LPA"
        },
        "growth": [
            "Junior Software Developer",
            "Software Developer",
            "Senior Software Engineer",
            "Technical Lead",
            "Software Architect"
        ],
        "description": (
            "Software Developers design, develop, test and maintain "
            "computer applications and software systems."
        ),
        "reason": (
            "Programming knowledge in languages such as Python, Java, "
            "C, C++ and C# supports software development."
        )
    }
}


# =========================================================
# CAREER KEYWORDS
# =========================================================

career_keywords = {
    "Python Developer": [
        "python", "coding", "programming", "backend", "automation"
    ],
    "Java Developer": [
        "java", "android", "backend", "software"
    ],
    "C/C++ Developer": [
        "c", "c++", "systems", "programming", "software"
    ],
    "Web Developer": [
        "web", "website", "development", "html", "css", "javascript"
    ],
    "Frontend Developer": [
        "frontend", "front end", "ui", "website", "design", "web"
    ],
    "Full Stack Developer": [
        "full stack", "web", "website", "backend", "frontend"
    ],
    "Data Analyst": [
        "data", "analysis", "analytics", "excel", "business", "statistics"
    ],
    "Data Scientist": [
        "data science", "machine learning", "ai",
        "artificial intelligence", "prediction", "data"
    ],
    "Database Developer": [
        "database", "sql", "mysql", "data", "database management"
    ],
    "DevOps Engineer": [
        "devops", "linux", "cloud", "deployment", "server", "networking"
    ],
    "UI/UX Designer": [
        "ui", "ux", "design", "creative", "figma", "photoshop"
    ],
    "Software Developer": [
        "software", "coding", "programming", "application", "development"
    ]
}


# =========================================================
# CAREER DETAILS
# =========================================================

career_details_data = {
    "Python Developer": {
        "technologies": ["Python", "Flask / Django", "FastAPI", "SQL", "Git", "Docker"],
        "roadmap": [
            "Master Python fundamentals (OOP, data structures, decorators, generators).",
            "Learn web frameworks like Flask or FastAPI for building RESTful APIs.",
            "Work with relational databases (SQLite, PostgreSQL) and ORMs (SQLAlchemy).",
            "Implement asynchronous programming and task queues (Celery, Redis).",
            "Build containerized portfolio projects with Docker and deploy to the cloud.",
            "Practice problem solving on LeetCode and prepare for system design rounds."
        ],
        "projects": [
            "Automated Multi-Source Web Scraper & Analytics Dashboard",
            "Scalable REST API with FastAPI, JWT Auth & PostgreSQL",
            "Full-Stack Task & Workflow Management SaaS"
        ],
        "resources": [
            "Official Python Documentation (python.org)",
            "Real Python Interactive Guides & Tutorials",
            "FastAPI & Flask Official Documentation",
            "GitHub Python Open-Source Repositories"
        ]
    },
    "Java Developer": {
        "technologies": ["Java", "Spring Boot", "Hibernate / JPA", "MySQL", "Maven / Gradle", "Microservices"],
        "roadmap": [
            "Learn Core Java, OOP principles, Collections framework, and Multithreading.",
            "Understand database schema design, SQL, and JDBC connections.",
            "Master Spring Boot framework for enterprise API and web development.",
            "Learn ORM tools like Hibernate / Spring Data JPA.",
            "Design Microservices architectures with Docker, Kafka, or RabbitMQ.",
            "Prepare for technical interviews with design patterns and algorithms."
        ],
        "projects": [
            "Online Banking & Transaction Ledger Simulation",
            "Enterprise E-Commerce Microservices Backend",
            "Student & Course Management System with Spring Boot & MySQL"
        ],
        "resources": [
            "Oracle Java Tutorials",
            "Spring.io Official Quickstart Guides",
            "Baeldung Java & Spring Articles",
            "GeeksforGeeks Java Programming"
        ]
    },
    "C/C++ Developer": {
        "technologies": ["C", "C++", "STL", "Memory Management", "Linux / POSIX", "CMake"],
        "roadmap": [
            "Master C syntax, pointers, memory allocation (malloc/free), and structs.",
            "Learn Modern C++ (C++17/20, STL, templates, smart pointers, RAII).",
            "Study operating systems, file I/O, threads, and Linux socket programming.",
            "Understand low-level debugging with GDB and Valgrind.",
            "Build performance-critical systems, libraries, or graphics projects.",
            "Prepare for system programming interviews and computer architecture questions."
        ],
        "projects": [
            "Custom Thread-Safe Dynamic Memory Allocator",
            "Lightweight HTTP Web Server from Scratch (Sockets API)",
            "Terminal-based Game / Physics Engine using SDL2"
        ],
        "resources": [
            "cppreference.com (C and C++ Reference)",
            "LearnCpp.com Free Modern C++ Tutorial",
            "The C Programming Language (Kernighan & Ritchie)",
            "Compiler Explorer (godbolt.org)"
        ]
    },
    "Web Developer": {
        "technologies": ["HTML5", "CSS3", "JavaScript", "Responsive Design", "Bootstrap / Tailwind", "Git"],
        "roadmap": [
            "Master semantic HTML5, CSS3 layout models (Flexbox, CSS Grid).",
            "Learn modern JavaScript (ES6+, DOM manipulation, Fetch API, Async/Await).",
            "Adopt modern CSS frameworks like Tailwind CSS or Bootstrap 5.",
            "Learn version control with Git and host websites on Vercel / Netlify / GitHub Pages.",
            "Learn basic backend integration and API consumption.",
            "Build responsive, accessible, cross-browser compatible web experiences."
        ],
        "projects": [
            "Responsive Creative Agency / SaaS Landing Page",
            "Interactive Personal Portfolio with Dark/Light Theme",
            "Product Catalog with Dynamic Filtering and Shopping Cart"
        ],
        "resources": [
            "MDN Web Docs (Mozilla Developer Network)",
            "Frontend Mentor UI Challenges",
            "FreeCodeCamp Responsive Web Design Certification",
            "CSS-Tricks Guides"
        ]
    },
    "Frontend Developer": {
        "technologies": ["JavaScript / TypeScript", "React / Vue", "Tailwind CSS", "Redux / Zustand", "Next.js"],
        "roadmap": [
            "Achieve deep proficiency in JavaScript and TypeScript fundamentals.",
            "Master modern frontend libraries (React.js, components, hooks, state).",
            "Learn global state management (Redux Toolkit, Zustand, Context API).",
            "Build server-rendered or static applications with Next.js.",
            "Optimize web performance (lazy loading, Lighthouse scores, core web vitals).",
            "Prepare frontend portfolio projects and practice UI coding challenges."
        ],
        "projects": [
            "Full-Featured Trello / Kanban Board with Drag-and-Drop",
            "Interactive Real-Time Crypto & Stock Market Tracker",
            "Modern Headless CMS Documentation / Blog Platform"
        ],
        "resources": [
            "React Official Documentation (react.dev)",
            "JavaScript.info Comprehensive Tutorial",
            "Tailwind CSS Documentation",
            "Roadmap.sh Frontend Developer Track"
        ]
    },
    "Full Stack Developer": {
        "technologies": ["React / Next.js", "Node.js / Express", "PostgreSQL / MongoDB", "REST & GraphQL", "Docker"],
        "roadmap": [
            "Solidify frontend development with React, TypeScript, and modern styling.",
            "Master backend development with Node.js/Express, Python/Flask, or Django.",
            "Learn relational (PostgreSQL) and NoSQL (MongoDB) databases and migrations.",
            "Implement secure authentication (OAuth2, JWT, sessions) and role-based access.",
            "Deploy full stack applications using Docker, cloud VPS, or platforms like AWS/Render.",
            "Build production-grade SaaS products with end-to-end testing and CI/CD."
        ],
        "projects": [
            "Collaborative Team Workspace & Task Management SaaS",
            "Full-Stack E-Commerce Store with Stripe Payment Integration",
            "Real-Time Chat & Discussion Community with WebSockets"
        ],
        "resources": [
            "The Odin Project Full Stack Curriculum",
            "Full Stack Open (University of Helsinki)",
            "FreeCodeCamp Full Stack Certification",
            "Roadmap.sh Full Stack Guide"
        ]
    },
    "Data Analyst": {
        "technologies": ["SQL", "Excel / Google Sheets", "Power BI / Tableau", "Python", "Data Visualization"],
        "roadmap": [
            "Master advanced Excel (VLOOKUP, XLOOKUP, Pivot Tables, Power Query).",
            "Learn SQL for data extraction, joins, subqueries, and window functions.",
            "Master business intelligence tools like Microsoft Power BI or Tableau.",
            "Learn Python for data analysis using Pandas, NumPy, Matplotlib, and Seaborn.",
            "Practice storytelling with data, translating metrics into business strategies.",
            "Publish interactive dashboards and case studies to your portfolio."
        ],
        "projects": [
            "Interactive Retail Sales & Profitability Dashboard (Power BI)",
            "E-Commerce Customer Retention & Churn SQL Analysis",
            "Comprehensive Exploratory Data Analysis (EDA) on Global Healthcare Data"
        ],
        "resources": [
            "Kaggle Learn Data Analysis Courses",
            "Maven Analytics Data Analyst Roadmap",
            "SQLZoo Interactive SQL Practice",
            "Storytelling with Data (Cole Nussbaumer)"
        ]
    },
    "Data Scientist": {
        "technologies": ["Python", "Pandas / NumPy", "Scikit-Learn", "Machine Learning", "Deep Learning", "Statistics"],
        "roadmap": [
            "Strengthen foundations in linear algebra, multivariable calculus, and statistics.",
            "Master Python data libraries: NumPy, Pandas, Scipy, and data wrangling.",
            "Master classic ML algorithms: Regression, Classification, Random Forests, XGBoost.",
            "Learn model evaluation, cross-validation, hyperparameter tuning, and pipelines.",
            "Explore Deep Learning with PyTorch or TensorFlow (NLP, Computer Vision).",
            "Deploy ML models as APIs using FastAPI or Flask and build interactive demos."
        ],
        "projects": [
            "Predictive Real Estate Valuation Model with Feature Engineering",
            "Customer Review Sentiment Analysis with NLP and Scikit-Learn",
            "End-to-End Disease Risk Prediction Web App with ML Pipeline"
        ],
        "resources": [
            "Scikit-Learn Documentation and User Guides",
            "Fast.ai Practical Deep Learning for Coders",
            "StatQuest with Josh Starmer (YouTube)",
            "Papers With Code Benchmark Studies"
        ]
    },
    "Database Developer": {
        "technologies": ["SQL", "PostgreSQL", "MySQL", "Database Design", "Indexing & Query Tuning", "PL/SQL"],
        "roadmap": [
            "Master relational theory, normalization (1NF to 3NF/BCNF), and ER modeling.",
            "Write complex queries, stored procedures, triggers, views, and functions.",
            "Learn query execution plans, indexing strategies, and database optimization.",
            "Study database security, ACID properties, transactions, and concurrency control.",
            "Explore backup/recovery strategies, replication, and high-availability setups.",
            "Understand NoSQL alternatives (Redis, Cassandra, MongoDB) for polyglot systems."
        ],
        "projects": [
            "Comprehensive Hospital Management Relational Schema with Constraints",
            "High-Throughput Financial Ledger Database with Stored Procedures",
            "Automated ETL Data Ingestion Pipeline with Database Triggers"
        ],
        "resources": [
            "Use The Index, Luke! (SQL Indexing Guide)",
            "PostgreSQL Official Documentation & Tutorials",
            "MySQL Performance Tuning Handbook",
            "Database System Concepts (Silberschatz, Korth)"
        ]
    },
    "DevOps Engineer": {
        "technologies": ["Linux / Bash", "Git", "Docker", "Kubernetes", "AWS / Azure", "CI/CD (GitHub Actions)"],
        "roadmap": [
            "Master Linux administration, shell scripting, networking, and security.",
            "Master Git workflows, branching strategies, and repository management.",
            "Containerize applications with Docker and compose multi-service environments.",
            "Build automated CI/CD pipelines with GitHub Actions or GitLab CI.",
            "Learn cloud providers (AWS/GCP/Azure) and Infrastructure as Code (Terraform).",
            "Orchestrate workloads with Kubernetes and set up monitoring (Prometheus/Grafana)."
        ],
        "projects": [
            "Automated Multi-Stage CI/CD Deployment with GitHub Actions",
            "Containerized Microservices Architecture with Docker Compose",
            "Production-Ready Kubernetes Deployment on Cloud with Monitoring"
        ],
        "resources": [
            "Roadmap.sh DevOps Roadmap",
            "Docker Official Documentation & Labs",
            "Kubernetes.io Tutorials (The Hard Way)",
            "AWS Free Tier & Certified Cloud Practitioner Guides"
        ]
    },
    "UI/UX Designer": {
        "technologies": ["Figma", "UI Design", "User Research", "Wireframing", "Prototyping", "Design Systems"],
        "roadmap": [
            "Master visual design principles: hierarchy, typography, color theory, and spacing.",
            "Master Figma: auto-layout, components, variants, variables, and prototyping.",
            "Learn user research methodologies: user interviews, persona creation, user flows.",
            "Design low-fidelity wireframes and test usability with interactive prototypes.",
            "Build comprehensive, scalable design systems and developer handoff documentation.",
            "Publish detailed UX case studies highlighting problem-solving and user outcomes."
        ],
        "projects": [
            "Mobile Food Delivery App End-to-End UX Case Study",
            "Fintech Analytics Dashboard & Component Design System in Figma",
            "Usability Audit & Redesign of an E-Commerce Checkout Flow"
        ],
        "resources": [
            "Figma Official Design Tutorials & Community",
            "Nielsen Norman Group (NN/g) UX Articles",
            "Laws of UX (lawsofux.com)",
            "Mobbin Mobile & Web Design Archive"
        ]
    },
    "Software Developer": {
        "technologies": ["Data Structures & Algorithms", "Java / Python / C++", "Git", "OOP & System Design", "Unit Testing"],
        "roadmap": [
            "Master core computer science fundamentals: algorithms, arrays, trees, graphs.",
            "Achieve deep proficiency in at least one modern language (Java, Python, C++, Go).",
            "Understand Object-Oriented Design, SOLID principles, and clean code standards.",
            "Write testable code with automated unit and integration tests.",
            "Learn fundamental system design concepts: caching, load balancing, databases.",
            "Solve coding problems regularly on LeetCode / HackerRank and build software projects."
        ],
        "projects": [
            "High-Performance Custom Data Structures Library with Benchmarks",
            "Desktop/CLI File Compression Utility using Huffman Encoding",
            "Modular Clean Architecture Application with Comprehensive Unit Tests"
        ],
        "resources": [
            "Refactoring.Guru (Design Patterns & Refactoring)",
            "System Design Primer (GitHub)",
            "Clean Code (Robert C. Martin)",
            "LeetCode & HackerRank"
        ]
    }
}


# =========================================================
# DATABASE INITIALIZATION & CAREER DYNAMIC LOADING
# =========================================================

def init_database():
    connection = sqlite3.connect(DATABASE)

    try:
        cursor = connection.cursor()

        # Users table for multi-user authentication
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT DEFAULT 'user',
                education TEXT DEFAULT '',
                skills TEXT DEFAULT '',
                languages TEXT DEFAULT '',
                career_goal TEXT DEFAULT '',
                about TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Careers table for admin management
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS careers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                description TEXT NOT NULL,
                reason TEXT NOT NULL,
                entry_salary TEXT NOT NULL,
                exp_salary TEXT NOT NULL,
                skills TEXT NOT NULL,
                roles TEXT NOT NULL,
                growth TEXT NOT NULL,
                roadmap TEXT NOT NULL,
                projects TEXT NOT NULL,
                resources TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # History table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NULL,
                user_email TEXT NULL,
                interest TEXT,
                skills TEXT,
                languages TEXT,
                top_career TEXT,
                match_percentage INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Ensure user_id and user_email columns exist in history
        cursor.execute("PRAGMA table_info(history)")
        hist_cols = [c[1] for c in cursor.fetchall()]
        if "user_id" not in hist_cols:
            cursor.execute("ALTER TABLE history ADD COLUMN user_id INTEGER NULL")
        if "user_email" not in hist_cols:
            cursor.execute("ALTER TABLE history ADD COLUMN user_email TEXT NULL")

        # Seed default Admin account if not present
        cursor.execute("SELECT COUNT(*) FROM users WHERE email = 'admin@careerai.com'")
        if cursor.fetchone()[0] == 0:
            admin_pw = generate_password_hash("admin123")
            cursor.execute("""
                INSERT INTO users (name, email, password_hash, role, education, career_goal, about)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                "System Administrator",
                "admin@careerai.com",
                admin_pw,
                "admin",
                "System Administration",
                "Platform & Model Management",
                "CareerAI Official Administrator Account"
            ))

        # Seed careers table from initial career_data if empty
        cursor.execute("SELECT COUNT(*) FROM careers")
        if cursor.fetchone()[0] == 0:
            for name, data in career_data.items():
                details = career_details_data.get(name, {})
                cursor.execute("""
                    INSERT INTO careers 
                    (name, description, reason, entry_salary, exp_salary, skills, roles, growth, roadmap, projects, resources)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    name,
                    data.get("description", ""),
                    data.get("reason", ""),
                    data.get("salary", {}).get("entry", ""),
                    data.get("salary", {}).get("experienced", ""),
                    json.dumps(data.get("skills", []), ensure_ascii=False),
                    json.dumps(data.get("roles", []), ensure_ascii=False),
                    json.dumps(data.get("growth", []), ensure_ascii=False),
                    json.dumps(details.get("roadmap", []), ensure_ascii=False),
                    json.dumps(details.get("projects", []), ensure_ascii=False),
                    json.dumps(details.get("resources", []), ensure_ascii=False)
                ))

        connection.commit()

    finally:
        connection.close()


def load_careers_from_db():
    """Load careers from database to allow real-time admin edits without restarting server."""
    global career_data, career_details_data
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row

    try:
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM careers ORDER BY name ASC")
        rows = cursor.fetchall()

        if rows:
            new_career_data = {}
            new_details_data = {}

            for r in rows:
                name = r["name"]
                skills = json.loads(r["skills"]) if r["skills"] else []
                roles = json.loads(r["roles"]) if r["roles"] else []
                growth = json.loads(r["growth"]) if r["growth"] else []
                roadmap = json.loads(r["roadmap"]) if r["roadmap"] else []
                projects = json.loads(r["projects"]) if r["projects"] else []
                resources = json.loads(r["resources"]) if r["resources"] else []

                new_career_data[name] = {
                    "skills": skills,
                    "roles": roles,
                    "salary": {
                        "entry": r["entry_salary"],
                        "experienced": r["exp_salary"]
                    },
                    "growth": growth,
                    "description": r["description"],
                    "reason": r["reason"]
                }
                new_details_data[name] = {
                    "technologies": skills,
                    "roadmap": roadmap,
                    "projects": projects,
                    "resources": resources
                }

            career_data = new_career_data
            career_details_data = new_details_data

    except Exception as error:
        print("Error loading careers from DB:", error)
    finally:
        connection.close()


init_database()
load_careers_from_db()


# =========================================================
# JINJA FILTERS & CONTEXT PROCESSORS
# =========================================================

@app.template_filter("from_json")
def from_json_filter(val):
    if not val:
        return []
    try:
        if isinstance(val, str):
            return json.loads(val)
        return val if isinstance(val, list) else []
    except Exception:
        return []


@app.context_processor
def inject_current_user():
    user_id = session.get("user_id")
    user_name = session.get("user_name")
    user_email = session.get("user_email")
    role = session.get("role", "user")

    return {
        "current_user": {
            "id": user_id,
            "name": user_name,
            "email": user_email,
            "role": role,
            "is_authenticated": bool(user_id),
            "is_admin": (role == "admin")
        }
    }


# =========================================================
# AUTHENTICATION DECORATORS
# =========================================================

def login_required(view_func):
    @wraps(view_func)
    def decorated_view(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please sign in to access your profile and history.", "info")
            return redirect(url_for("login", next=request.path))
        return view_func(*args, **kwargs)
    return decorated_view


def admin_required(view_func):
    @wraps(view_func)
    def decorated_view(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please sign in with administrator credentials.", "warning")
            return redirect(url_for("login", next=request.path))
        if session.get("role") != "admin":
            flash("Access denied. Administrator privileges are required to view this panel.", "error")
            return redirect(url_for("home"))
        return view_func(*args, **kwargs)
    return decorated_view


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def allowed_file(filename):
    return (
        bool(filename)
        and "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


def skill_found(skill, text):
    """Find a skill as a separate term, including skills like C++ and C#."""
    if not skill or not text:
        return False

    skill = skill.strip().lower()
    text = text.lower()

    # Programming names with symbols need explicit boundaries.
    escaped_skill = re.escape(skill)
    pattern = r"(?<![a-z0-9])" + escaped_skill + r"(?![a-z0-9])"

    return re.search(pattern, text, flags=re.IGNORECASE) is not None


def extract_pdf_text(file_path):
    text = ""

    try:
        reader = PdfReader(file_path)

        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"

    except Exception as error:
        print("PDF extraction error:", error)

    return text


def extract_docx_text(file_path):
    text = ""

    try:
        document = Document(file_path)

        for paragraph in document.paragraphs:
            if paragraph.text.strip():
                text += paragraph.text + "\n"

        for table in document.tables:
            for row in table.rows:
                for cell in row.cells:
                    if cell.text.strip():
                        text += cell.text + " "
                text += "\n"

    except Exception as error:
        print("DOCX extraction error:", error)

    return text


def extract_resume_text(file_path, extension):
    if extension == "pdf":
        return extract_pdf_text(file_path)

    if extension == "docx":
        return extract_docx_text(file_path)

    return ""


def detect_resume_skills(resume_text):
    all_skills = set()

    for data in career_data.values():
        for skill in data["skills"]:
            if skill_found(skill, resume_text):
                all_skills.add(skill)

    return sorted(all_skills, key=lambda value: value.lower())


def calculate_resume_careers(resume_text):
    scores = {}

    for career, data in career_data.items():
        score = 0

        for skill in data["skills"]:
            if skill_found(skill, resume_text):
                score += 12

        for keyword in career_keywords.get(career, []):
            if keyword.lower() in resume_text.lower():
                score += 8

        scores[career] = score

    return scores


def email_found(text):
    return re.search(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
        text
    ) is not None


def safe_ml_prediction(model_text):
    """Return the prediction and confidence, or safe defaults if ML fails."""
    prediction = None
    confidence = 0.0

    if model is None:
        return prediction, confidence

    try:
        prediction = str(model.predict([model_text])[0])

        if hasattr(model, "predict_proba"):
            probabilities = model.predict_proba([model_text])[0]
            confidence = float(max(probabilities)) * 100

    except Exception as error:
        print("ML prediction error:", error)

    return prediction, confidence


def calculate_match_percentage(score, maximum_score):
    if maximum_score <= 0:
        return 0

    return max(0, min(98, round((score / maximum_score) * 100)))


# =========================================================
# HOME & EXPLORE CAREERS
# =========================================================

@app.route("/")
def home():
    profile_data = None
    user_id = session.get("user_id")
    if user_id:
        connection = sqlite3.connect(DATABASE)
        connection.row_factory = sqlite3.Row
        try:
            cursor = connection.cursor()
            cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            profile_data = cursor.fetchone()
        finally:
            connection.close()

    return render_template("index.html", profile=profile_data)


@app.route("/careers")
def list_careers():
    return render_template("careers.html", careers=career_data)


# =========================================================
# CAREER PREDICTION
# =========================================================

@app.route("/predict", methods=["POST"])
def predict():
    interest = request.form.get("interest", "").strip()
    skill = request.form.get("skill", request.form.get("skills", "")).strip()
    selected_languages = request.form.getlist("languages")

    session["career_input"] = {
        "interest": interest,
        "skill": skill,
        "selected_languages": selected_languages
    }

    interest_lower = interest.lower()
    skills_text = skill.lower()
    selected_lower = [language.lower() for language in selected_languages]

    career_scores = {}

    for career, data in career_data.items():
        score = 0

        for required_skill in data["skills"]:
            if required_skill.lower() in selected_lower:
                score += 12

            if skill_found(required_skill, skills_text):
                score += 5

        for keyword in career_keywords.get(career, []):
            if keyword in interest_lower:
                score += 10

        career_scores[career] = score

    model_text = (
        interest + " " + skill + " " + " ".join(selected_languages)
    )

    ml_prediction, ml_confidence = safe_ml_prediction(model_text)

    # Apply the ML bonus only if the model label matches a known career.
    if ml_prediction in career_scores:
        career_scores[ml_prediction] += 20

    sorted_careers = sorted(
        career_scores.items(),
        key=lambda item: item[1],
        reverse=True
    )

    top_five = sorted_careers[:5]
    careers = []

    for career, score in top_five:
        data = career_data[career]

        maximum_score = (
            len(data["skills"]) * 12
            + len(data["skills"]) * 5
            + len(career_keywords.get(career, [])) * 10
            + 20
        )

        percentage = calculate_match_percentage(score, maximum_score)
        careers.append((career, percentage))

    if not careers:
        careers = [("Software Developer", 0)]

    top_career = careers[0][0]
    top_percentage = careers[0][1]
    top_data = career_data[top_career]

    matched_interest_keywords = [
        keyword
        for keyword in career_keywords.get(top_career, [])
        if keyword in interest_lower
    ]

    interest_score = min(30, len(matched_interest_keywords) * 10)

    matched_skills = []
    missing_skills = []

    for required_skill in top_data["skills"]:
        if (
            required_skill.lower() in selected_lower
            or skill_found(required_skill, skills_text)
        ):
            matched_skills.append(required_skill)
        else:
            missing_skills.append(required_skill)

    skill_score = min(50, len(matched_skills) * 8)

    total_required_skills = len(top_data["skills"])

    readiness_score = (
        round(len(matched_skills) / total_required_skills * 100)
        if total_required_skills else 0
    )

    skill_gap_percentage = max(0, 100 - readiness_score)

    if readiness_score >= 80:
        readiness_label = "Strong career readiness"
    elif readiness_score >= 50:
        readiness_label = "Moderate career readiness"
    elif readiness_score > 0:
        readiness_label = "Early-stage career readiness"
    else:
        readiness_label = "Start building the required skills"

    ml_bonus = 20 if ml_prediction == top_career else 0
    overall_score = min(100, interest_score + skill_score + ml_bonus)

    analysis_parts = []

    if matched_interest_keywords:
        analysis_parts.append(
            "Your interests match this career through "
            + ", ".join(matched_interest_keywords[:4])
            + "."
        )
    else:
        analysis_parts.append(
            "Your current interest description has limited "
            "direct keyword matches with this career."
        )

    if matched_skills:
        analysis_parts.append(
            "You already have relevant skills such as "
            + ", ".join(matched_skills[:5])
            + "."
        )
    else:
        analysis_parts.append(
            "No core technical skills for this career were detected "
            "in your selected skills or skill description yet."
        )

    if missing_skills:
        analysis_parts.append(
            "The main skills to improve are "
            + ", ".join(missing_skills[:5])
            + "."
        )
    else:
        analysis_parts.append(
            "You currently match all the listed core skills for this career."
        )

    if ml_prediction:
        if ml_prediction == top_career:
            analysis_parts.append(
                "The Machine Learning model also predicted "
                + ml_prediction
                + ", which supports this recommendation."
            )
        else:
            analysis_parts.append(
                "The Machine Learning model predicted "
                + ml_prediction
                + ". The final result also considers your interests "
                "and technical skills."
            )

    ai_analysis = " ".join(analysis_parts)

    if ml_confidence >= 80:
        confidence = "Very High"
    elif ml_confidence >= 60:
        confidence = "High"
    elif ml_confidence >= 40:
        confidence = "Moderate"
    else:
        confidence = "Low"

    next_skills = missing_skills[:5]
    recommended_job_roles = top_data["roles"]

    roadmap = [
        f"Learn and practice {missing_skill}."
        for missing_skill in missing_skills[:5]
    ]

    roadmap.extend([
        f"Build projects related to {top_career}.",
        "Update your resume with measurable project achievements.",
        "Create or improve your GitHub portfolio.",
        "Prepare for technical interviews."
    ])

    resources = [
        "Official documentation and programming tutorials",
        "Online coding practice platforms",
        "Project-based learning",
        "GitHub for portfolio projects",
        "Technical interview preparation resources"
    ]

    tips = [
        "Build practical projects instead of only studying theory.",
        "Keep your GitHub profile updated.",
        "Practice coding regularly.",
        "Learn one technology deeply before adding too many new ones.",
        "Apply for internships and entry-level opportunities."
    ]

    connection = None

    try:
        connection = sqlite3.connect(DATABASE)
        cursor = connection.cursor()

        user_id = session.get("user_id")
        user_email = session.get("user_email", "Guest")

        cursor.execute("""
            INSERT INTO history
            (user_id, user_email, interest, skills, languages, top_career, match_percentage)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            user_email,
            interest,
            skill,
            ", ".join(selected_languages),
            top_career,
            top_percentage
        ))

        connection.commit()
        print("Career prediction saved to history.")

    except sqlite3.Error as error:
        print("Database error:", error)

    finally:
        if connection:
            connection.close()

    session["comparison_careers"] = [career for career, _ in careers]
    session["comparison_scores"] = {
        career: percentage for career, percentage in careers
    }

    result_context = {
        "interest": interest,
        "skill": skill,
        "selected_languages": selected_languages,
        "ai_analysis": ai_analysis,
        "careers": careers,
        "recommended_job_roles": recommended_job_roles,
        "top_career": top_career,
        "salary": top_data.get("salary", {
            "entry": "Not available",
            "experienced": "Not available"
        }),
        "growth": top_data.get("growth", []),
        "interest_score": interest_score,
        "skill_score": skill_score,
        "overall_score": overall_score,
        "readiness_score": readiness_score,
        "readiness_label": readiness_label,
        "skill_gap_percentage": skill_gap_percentage,
        "next_skills": next_skills,
        "ml_confidence": round(ml_confidence, 1),
        "confidence": confidence,
        "description": top_data.get("description", ""),
        "reason": top_data.get("reason", ""),
        "have_skills": matched_skills,
        "missing_skills": missing_skills,
        "roadmap": roadmap,
        "resources": resources,
        "tips": tips
    }

    result_token = save_temporary_result("career", result_context)
    return redirect(url_for("show_career_result", token=result_token), code=303)


@app.route("/result/<token>")
def show_career_result(token):
    result_context = load_temporary_result(token, "career")

    if result_context is None:
        return redirect(url_for("home"))

    return render_template("result.html", **result_context)


# =========================================================
# CAREER COMPARISON
# =========================================================

@app.route("/compare")
def compare_careers():
    # Check if specific careers were requested via query parameter ?c=
    requested = request.args.getlist("c")
    if not requested and request.args.get("c"):
        requested = [request.args.get("c")]

    comparison_scores = session.get("comparison_scores", {})
    session_careers = session.get("comparison_careers", [])

    if requested:
        comparison_careers = [c for c in requested if c in career_data]
    elif session_careers:
        comparison_careers = [c for c in session_careers if c in career_data]
    else:
        comparison_careers = ["Full Stack Developer", "Python Developer", "Data Scientist"]

    # Filter out empty or duplicate selections while preserving order
    unique_careers = []
    for c in comparison_careers:
        if c and c in career_data and c not in unique_careers:
            unique_careers.append(c)

    if len(unique_careers) < 2:
        # Ensure at least two careers for meaningful comparison
        for fallback in ["Python Developer", "Full Stack Developer", "Data Scientist"]:
            if fallback not in unique_careers:
                unique_careers.append(fallback)
            if len(unique_careers) >= 2:
                break

    comparison_data = []
    for career in unique_careers:
        data = career_data[career]
        comparison_data.append({
            "name": career,
            "match": int(comparison_scores.get(career, 0)),
            "skills": data["skills"],
            "roles": data["roles"],
            "salary": data["salary"],
            "growth": data["growth"]
        })

    return render_template(
        "compare.html",
        comparison_data=comparison_data,
        all_careers=list(career_data.keys()),
        selected_careers=unique_careers
    )


# =========================================================
# CAREER DETAILS
# =========================================================

@app.route("/career-details/<path:career_name>")
def career_details(career_name):
    if career_name not in career_data:
        return redirect(url_for("home"))

    data = career_data[career_name]
    details = career_details_data.get(career_name, {})

    return render_template(
        "career_details.html",
        career_name=career_name,
        data=data,
        technologies=details.get("technologies", data.get("skills", [])),
        roadmap=details.get("roadmap", []),
        projects=details.get("projects", []),
        resources=details.get("resources", [])
    )


# =========================================================
# SKILL GAP ANALYZER
# =========================================================

@app.route("/skill-gap/<path:career_name>")
def skill_gap(career_name):
    if career_name not in career_data:
        return redirect(url_for("home"))

    data = career_data[career_name]
    saved = session.get("career_input", {})

    skill_text = saved.get("skill", "").lower()
    selected_languages = [
        item.lower()
        for item in saved.get("selected_languages", [])
    ]

    # If no session data, fallback to user's saved profile
    if not skill_text and not selected_languages:
        connection = sqlite3.connect(DATABASE)
        connection.row_factory = sqlite3.Row
        try:
            cursor = connection.cursor()
            user_id = session.get("user_id")
            if user_id:
                cursor.execute("SELECT skills, languages FROM users WHERE id = ?", (user_id,))
            else:
                cursor.execute("SELECT skills, languages FROM users LIMIT 1")
            user_profile = cursor.fetchone()
            if user_profile:
                if user_profile["skills"]:
                    skill_text = user_profile["skills"].lower()
                if user_profile["languages"]:
                    selected_languages = [
                        item.strip().lower()
                        for item in user_profile["languages"].split(",")
                        if item.strip()
                    ]
        finally:
            connection.close()

    matched_skills = []
    missing_skills = []

    for required_skill in data.get("skills", []):
        if (
            required_skill.lower() in selected_languages
            or skill_found(required_skill, skill_text)
        ):
            matched_skills.append(required_skill)
        else:
            missing_skills.append(required_skill)

    total_skills = len(data.get("skills", []))

    readiness_score = (
        round(len(matched_skills) / total_skills * 100)
        if total_skills else 0
    )

    skill_gap_percentage = max(0, 100 - readiness_score)

    if readiness_score >= 80:
        readiness_label = "Strong career readiness"
    elif readiness_score >= 50:
        readiness_label = "Moderate career readiness"
    elif readiness_score > 0:
        readiness_label = "Early-stage career readiness"
    else:
        readiness_label = "Start building the required skills"

    return render_template(
        "skill_gap.html",
        career_name=career_name,
        readiness_score=readiness_score,
        readiness_label=readiness_label,
        skill_gap_percentage=skill_gap_percentage,
        matched_skills=matched_skills,
        missing_skills=missing_skills
    )


# =========================================================
# AI CAREER INSIGHTS
# =========================================================

@app.route("/career-insights/<path:career_name>")
def career_insights(career_name):
    if career_name not in career_data:
        return redirect(url_for("home"))

    data = career_data[career_name]
    saved = session.get("career_input", {})

    interest_text = saved.get("interest", "").lower()
    skill_text = saved.get("skill", "").lower()

    selected_languages = [
        item.lower()
        for item in saved.get("selected_languages", [])
    ]

    # If no session data, fallback to user's saved profile
    if not interest_text and not skill_text and not selected_languages:
        connection = sqlite3.connect(DATABASE)
        connection.row_factory = sqlite3.Row
        try:
            cursor = connection.cursor()
            user_id = session.get("user_id")
            if user_id:
                cursor.execute("SELECT skills, languages, career_goal, about FROM users WHERE id = ?", (user_id,))
            else:
                cursor.execute("SELECT skills, languages, career_goal, about FROM users LIMIT 1")
            user_profile = cursor.fetchone()
            if user_profile:
                interest_text = ((user_profile["career_goal"] or "") + " " + (user_profile["about"] or "")).lower()
                if user_profile["skills"]:
                    skill_text = user_profile["skills"].lower()
                if user_profile["languages"]:
                    selected_languages = [
                        item.strip().lower()
                        for item in user_profile["languages"].split(",")
                        if item.strip()
                    ]
        finally:
            connection.close()

    matched_skills = []
    missing_skills = []

    for required_skill in data.get("skills", []):
        if (
            required_skill.lower() in selected_languages
            or skill_found(required_skill, skill_text)
        ):
            matched_skills.append(required_skill)
        else:
            missing_skills.append(required_skill)

    keywords = career_keywords.get(career_name, [])

    matched_keywords = [
        keyword for keyword in keywords
        if keyword in interest_text
    ]

    skill_percentage = (
        round(len(matched_skills) / len(data["skills"]) * 100)
        if data.get("skills") else 0
    )

    interest_percentage = min(100, len(matched_keywords) * 20)

    ml_prediction, ml_confidence = safe_ml_prediction(
        interest_text + " " + skill_text
    )

    if not ml_prediction:
        ml_prediction = "Not available"

    reasons = []

    if matched_keywords:
        reasons.append(
            "Your interests contain keywords related to this career."
        )

    if matched_skills:
        reasons.append(
            "You already have some skills required for this career."
        )

    if not reasons:
        reasons.append(
            "This career is one of the available paths in the AI Career Guidance system."
        )

    strengths = (
        matched_skills[:5]
        if matched_skills
        else ["Willingness to learn and develop new skills"]
    )

    improvement_steps = [
        "Work on the missing skills shown above.",
        "Practice through small hands-on projects.",
        "Build one portfolio project related to this career.",
        "Learn Git and maintain your GitHub profile.",
        "Prepare for internships and entry-level interviews."
    ]

    return render_template(
        "career_insights.html",
        career=career_name,
        description=data.get("description", ""),
        reasons=reasons,
        reason=" ".join(reasons),
        skill_percentage=skill_percentage,
        interest_percentage=interest_percentage,
        ml_prediction=ml_prediction,
        ml_confidence=round(ml_confidence),
        strengths=strengths,
        matched_skills=matched_skills,
        missing_skills=missing_skills,
        improvement_steps=improvement_steps
    )


# =========================================================
# RESUME PAGE
# =========================================================

@app.route("/resume")
def resume():
    return render_template("resume.html")


# =========================================================
# AI RESUME ANALYZER
# =========================================================

@app.route("/analyze-resume", methods=["POST"])
def analyze_resume():
    if "resume" not in request.files:
        return render_template(
            "resume.html",
            error="Please select a resume file."
        )

    resume_file = request.files["resume"]

    if resume_file.filename == "":
        return render_template(
            "resume.html",
            error="Please select a resume file."
        )

    if not allowed_file(resume_file.filename):
        return render_template(
            "resume.html",
            error="Only PDF and DOCX files are supported."
        )

    original_filename = secure_filename(resume_file.filename)

    if not original_filename or "." not in original_filename:
        return render_template(
            "resume.html",
            error="Please select a valid PDF or DOCX file."
        )

    extension = original_filename.rsplit(".", 1)[1].lower()

    # A unique temporary filename avoids collisions between uploads.
    filename = f"{uuid.uuid4().hex}_{original_filename}"
    file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)

    try:
        resume_file.save(file_path)
        resume_text = extract_resume_text(file_path, extension)

    except Exception as error:
        print("Resume processing error:", error)
        return render_template(
            "resume.html",
            error="Unable to process the resume."
        )

    finally:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError as error:
                print("Temporary resume cleanup error:", error)

    if not resume_text.strip():
        return render_template(
            "resume.html",
            error=(
                "No readable text was found in the resume. "
                "Please upload a text-based PDF or DOCX file."
            )
        )

    resume_text_lower = resume_text.lower()

    # DETECT SKILLS
    detected_skills = detect_resume_skills(resume_text)

    # CAREER MATCHING
    career_scores = calculate_resume_careers(resume_text)

    # MACHINE LEARNING PREDICTION
    ml_prediction, ml_confidence = safe_ml_prediction(resume_text)

    if ml_prediction in career_scores:
        career_scores[ml_prediction] += 20

    sorted_careers = sorted(
        career_scores.items(),
        key=lambda item: item[1],
        reverse=True
    )

    # TOP CAREER
    top_career = sorted_careers[0][0]
    top_data = career_data[top_career]

    max_possible = (
        len(top_data["skills"]) * 12
        + len(career_keywords.get(top_career, [])) * 8
        + 20
    )

    raw_score = career_scores[top_career]
    career_match = calculate_match_percentage(raw_score, max_possible)

    # MATCHED / MISSING SKILLS
    matched_skills = []
    missing_skills = []

    for skill_name in top_data["skills"]:
        if skill_found(skill_name, resume_text_lower):
            matched_skills.append(skill_name)
        else:
            missing_skills.append(skill_name)

    # RESUME SCORE
    resume_score = 0

    if detected_skills:
        resume_score += 30

    if any(word in resume_text_lower for word in [
        "education", "degree", "b.sc", "bsc", "b.tech",
        "btech", "m.sc", "msc", "m.tech", "college", "university"
    ]):
        resume_score += 15

    if any(word in resume_text_lower for word in [
        "experience", "internship", "intern", "work experience", "project"
    ]):
        resume_score += 15

    if email_found(resume_text):
        resume_score += 10

    if re.search(r"\b\d{10}\b", resume_text):
        resume_score += 10

    if "project" in resume_text_lower:
        resume_score += 10

    word_count = len(resume_text.split())

    if word_count >= 150:
        resume_score += 10

    resume_score = min(100, resume_score)

    # ATS CHECKS
    ats_checks = []

    if "education" in resume_text_lower:
        ats_checks.append(("Education section", "Present"))
    else:
        ats_checks.append(("Education section", "Missing"))

    if "experience" in resume_text_lower or "internship" in resume_text_lower:
        ats_checks.append(("Experience section", "Present"))
    else:
        ats_checks.append(("Experience section", "Missing"))

    if "project" in resume_text_lower:
        ats_checks.append(("Projects section", "Present"))
    else:
        ats_checks.append(("Projects section", "Missing"))

    if detected_skills:
        ats_checks.append(("Technical skills", "Detected"))
    else:
        ats_checks.append(("Technical skills", "Not detected"))

    if email_found(resume_text):
        ats_checks.append(("Email address", "Detected"))
    else:
        ats_checks.append(("Email address", "Missing"))

    # SUGGESTIONS
    suggestions = []

    if not detected_skills:
        suggestions.append(
            "Add a clear technical skills section with the technologies you know."
        )

    if "project" not in resume_text_lower:
        suggestions.append(
            "Add academic or personal projects with technologies used and your contribution."
        )

    if (
        "experience" not in resume_text_lower
        and "internship" not in resume_text_lower
    ):
        suggestions.append(
            "Add internship, training or practical experience if available."
        )

    if "education" not in resume_text_lower:
        suggestions.append("Add a clear Education section.")

    if not email_found(resume_text):
        suggestions.append("Add a professional email address.")

    if not suggestions:
        suggestions.append(
            "Your resume contains the major sections detected by the analyzer. "
            "Continue improving project descriptions and career-specific skills."
        )

    # LEARNING ROADMAP
    learning_roadmap = [
        f"Learn and practice {skill_name}."
        for skill_name in missing_skills[:5]
    ]

    learning_roadmap.extend([
        f"Build projects related to {top_career}.",
        "Update your resume with measurable project achievements.",
        "Create or improve your GitHub portfolio.",
        "Prepare for technical interviews."
    ])

    # AI RESUME ANALYSIS
    if ml_prediction:
        ai_resume_analysis = (
            f"The resume analysis identified {top_career} as the strongest "
            f"career direction. The Machine Learning model also predicted "
            f"{ml_prediction}. Your resume currently has a {career_match}% career match."
        )
    else:
        ai_resume_analysis = (
            f"Based on the skills and keywords detected in your resume, "
            f"{top_career} is the strongest career direction with a "
            f"{career_match}% match."
        )

    # RECOMMENDED ROLES
    recommended_roles = top_data["roles"]

    # OTHER CAREERS
    other_careers = []

    for career, score in sorted_careers[:5]:
        if career == top_career:
            continue

        other_score = min(95, max(0, int(score * 1.5)))
        other_careers.append((career, other_score))

    salary = top_data.get("salary", {
        "entry": "Not available",
        "experienced": "Not available"
    })

    growth = top_data.get("growth", [])
    roadmap = learning_roadmap

    resources = [
        "Official documentation and programming tutorials",
        "Online coding practice platforms",
        "Project-based learning",
        "GitHub for portfolio projects",
        "Technical interview preparation resources"
    ]

    tips = [
        "Build practical projects instead of only studying theory.",
        "Keep your GitHub profile updated.",
        "Practice coding regularly.",
        "Learn one technology deeply before adding too many new ones.",
        "Apply for internships and entry-level opportunities."
    ]

    careers = [(top_career, career_match)] + other_careers

    # SAVE SESSION DATA
    session["last_top_career"] = top_career
    session["last_ml_prediction"] = ml_prediction
    session["last_ml_confidence"] = round(ml_confidence)
    session["last_languages"] = detected_skills
    session["last_skill_text"] = ", ".join(detected_skills)

    # RESUME RESULT DATA
    result_context = {
        "filename": original_filename,
        "resume_score": resume_score,
        "career_match": career_match,
        "top_career": top_career,
        "detected_skills": detected_skills,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "ats_checks": ats_checks,
        "suggestions": suggestions,
        "learning_roadmap": learning_roadmap,
        "roadmap": roadmap,
        "salary": salary,
        "growth": growth,
        "resources": resources,
        "tips": tips,
        "careers": careers,
        "recommended_job_roles": recommended_roles,
        "recommended_roles": recommended_roles,
        "other_careers": other_careers,
        "ai_resume_analysis": ai_resume_analysis,
        "ml_prediction": ml_prediction,
        "ml_confidence": round(ml_confidence),
        "word_count": word_count
    }

    result_token = save_temporary_result("resume", result_context)

    return redirect(
        url_for("show_resume_result", token=result_token),
        code=303
    )


@app.route("/resume-result/<token>")
def show_resume_result(token):
    result_context = load_temporary_result(token, "resume")

    if result_context is None:
        return redirect(url_for("resume"))

    return render_template("resume_result.html", **result_context)


# =========================================================
# HISTORY
# =========================================================

@app.route("/history")
def history():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row

    try:
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM history ORDER BY id DESC")
        history_data = cursor.fetchall()
    finally:
        connection.close()

    return render_template("history.html", history=history_data)


# =========================================================
# DASHBOARD
# =========================================================

@app.route("/dashboard")
def dashboard():
    connection = sqlite3.connect(DATABASE)

    try:
        cursor = connection.cursor()

        cursor.execute("SELECT COUNT(*) FROM history")
        total_predictions = cursor.fetchone()[0]

        cursor.execute("SELECT AVG(match_percentage) FROM history")
        average_result = cursor.fetchone()[0]

        average_match = round(average_result) if average_result is not None else 0

        cursor.execute("""
            SELECT top_career, COUNT(*)
            FROM history
            GROUP BY top_career
            ORDER BY COUNT(*) DESC
        """)

        career_counts = dict(cursor.fetchall())

        top_career = (
            max(career_counts, key=career_counts.get)
            if career_counts else "No Data"
        )

    finally:
        connection.close()

    return render_template(
        "dashboard.html",
        total_predictions=total_predictions,
        average_match=average_match,
        top_career=top_career,
        career_counts=career_counts
    )


# =========================================================
# USER AUTHENTICATION (LOGIN, REGISTER, LOGOUT)
# =========================================================

@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        if session.get("role") == "admin":
            return redirect(url_for("admin_dashboard"))
        return redirect(url_for("profile"))

    next_url = request.args.get("next") or request.form.get("next")

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        connection = sqlite3.connect(DATABASE)
        connection.row_factory = sqlite3.Row
        try:
            cursor = connection.cursor()
            cursor.execute("SELECT * FROM users WHERE LOWER(email) = ?", (email,))
            user = cursor.fetchone()

            if user and check_password_hash(user["password_hash"], password):
                session["user_id"] = user["id"]
                session["user_name"] = user["name"]
                session["user_email"] = user["email"]
                session["role"] = user["role"]
                flash(f"Welcome back, {user['name']}!", "success")

                if next_url and next_url.startswith("/"):
                    return redirect(next_url)
                if user["role"] == "admin":
                    return redirect(url_for("admin_dashboard"))
                return redirect(url_for("profile"))
            else:
                flash("Invalid email or password. Please verify your credentials.", "error")
        finally:
            connection.close()

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("profile"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        education = request.form.get("education", "").strip()
        career_goal = request.form.get("career_goal", "").strip()

        if not name or not email or not password:
            flash("Please fill in all required fields.", "error")
            return render_template("register.html")

        if password != confirm:
            flash("Passwords do not match.", "error")
            return render_template("register.html")

        if len(password) < 6:
            flash("Password must be at least 6 characters.", "error")
            return render_template("register.html")

        connection = sqlite3.connect(DATABASE)
        connection.row_factory = sqlite3.Row
        try:
            cursor = connection.cursor()
            cursor.execute("SELECT id FROM users WHERE LOWER(email) = ?", (email,))
            if cursor.fetchone():
                flash("An account with this email already exists. Please sign in.", "error")
                return render_template("register.html")

            pw_hash = generate_password_hash(password)
            cursor.execute("""
                INSERT INTO users (name, email, password_hash, role, education, career_goal)
                VALUES (?, ?, ?, 'user', ?, ?)
            """, (name, email, pw_hash, education, career_goal))
            connection.commit()
            new_id = cursor.lastrowid

            session["user_id"] = new_id
            session["user_name"] = name
            session["user_email"] = email
            session["role"] = "user"

            flash("Account registered successfully! Welcome to CareerAI.", "success")
            return redirect(url_for("profile"))
        finally:
            connection.close()

    return render_template("register.html")


@app.route("/logout")
def logout():
    session.pop("user_id", None)
    session.pop("user_name", None)
    session.pop("user_email", None)
    session.pop("role", None)
    flash("You have successfully signed out.", "info")
    return redirect(url_for("login"))


# =========================================================
# PROFILE (LOGGED-IN USER)
# =========================================================

@app.route("/profile")
@login_required
def profile():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row

    try:
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (session["user_id"],))
        profile_data = cursor.fetchone()
    finally:
        connection.close()

    if not profile_data:
        flash("Profile not found. Please log in again.", "warning")
        return redirect(url_for("logout"))

    return render_template("profile.html", profile=profile_data)


@app.route("/edit-profile", methods=["GET", "POST"])
@login_required
def edit_profile():
    user_id = session["user_id"]

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email_address = request.form.get("email", "").strip().lower()
        education = request.form.get("education", "").strip()
        skills = request.form.get("skills", "").strip()
        languages = request.form.get("languages", "").strip()
        career_goal = request.form.get("career_goal", "").strip()
        about = request.form.get("about", "").strip()

        connection = sqlite3.connect(DATABASE)

        try:
            cursor = connection.cursor()
            cursor.execute("""
                UPDATE users
                SET name = ?, email = ?, education = ?, skills = ?,
                    languages = ?, career_goal = ?, about = ?
                WHERE id = ?
            """, (
                name,
                email_address,
                education,
                skills,
                languages,
                career_goal,
                about,
                user_id
            ))

            connection.commit()
            session["user_name"] = name
            session["user_email"] = email_address
        finally:
            connection.close()

        flash("Profile updated successfully!", "success")
        return redirect(url_for("profile"))

    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row

    try:
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        profile_data = cursor.fetchone()
    finally:
        connection.close()

    return render_template("edit_profile.html", profile=profile_data)


# =========================================================
# CLEAR HISTORY
# =========================================================

@app.route("/clear-history", methods=["GET", "POST"])
def clear_history():
    connection = sqlite3.connect(DATABASE)

    try:
        cursor = connection.cursor()
        if session.get("role") == "admin":
            cursor.execute("DELETE FROM history")
        elif session.get("user_id"):
            cursor.execute("DELETE FROM history WHERE user_id = ? OR user_email = ?", (session["user_id"], session.get("user_email")))
        else:
            cursor.execute("DELETE FROM history WHERE user_id IS NULL")
        connection.commit()
    finally:
        connection.close()

    flash("Assessment history has been cleared.", "info")
    return redirect(url_for("history"))


# =========================================================
# ADMIN CONSOLE (DASHBOARD, USERS, CAREERS, LOGS)
# =========================================================

@app.route("/admin")
@admin_required
def admin_dashboard():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row

    try:
        cursor = connection.cursor()

        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM history")
        total_history = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM careers")
        total_careers = cursor.fetchone()[0]

        cursor.execute("SELECT AVG(match_percentage) FROM history")
        avg_res = cursor.fetchone()[0]
        avg_match = round(avg_res) if avg_res else 0

        cursor.execute("SELECT * FROM users ORDER BY id DESC LIMIT 6")
        recent_users = cursor.fetchall()

        cursor.execute("SELECT * FROM history ORDER BY id DESC LIMIT 6")
        recent_logs = cursor.fetchall()

        cursor.execute("""
            SELECT top_career, COUNT(*) as cnt
            FROM history
            GROUP BY top_career
            ORDER BY cnt DESC
        """)
        career_counts = dict(cursor.fetchall())

        stats = {
            "total_users": total_users,
            "total_history": total_history,
            "total_careers": total_careers,
            "avg_match": avg_match
        }
    finally:
        connection.close()

    return render_template(
        "admin/dashboard.html",
        stats=stats,
        recent_users=recent_users,
        recent_logs=recent_logs,
        career_counts=career_counts
    )


@app.route("/admin/users")
@admin_required
def admin_users():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row

    try:
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM users ORDER BY id DESC")
        users = cursor.fetchall()

        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM careers")
        total_careers = cursor.fetchone()[0]
        stats = {"total_users": total_users, "total_careers": total_careers}
    finally:
        connection.close()

    return render_template("admin/users.html", users=users, stats=stats)


@app.route("/admin/users/<int:user_id>/edit", methods=["GET", "POST"])
@admin_required
def admin_edit_user(user_id):
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row

    try:
        cursor = connection.cursor()

        if request.method == "POST":
            name = request.form.get("name", "").strip()
            email = request.form.get("email", "").strip().lower()
            role = request.form.get("role", "user")
            education = request.form.get("education", "").strip()
            career_goal = request.form.get("career_goal", "").strip()
            skills = request.form.get("skills", "").strip()
            languages = request.form.get("languages", "").strip()
            about = request.form.get("about", "").strip()
            new_pw = request.form.get("new_password", "").strip()

            if new_pw:
                pw_hash = generate_password_hash(new_pw)
                cursor.execute("""
                    UPDATE users
                    SET name = ?, email = ?, role = ?, education = ?, career_goal = ?,
                        skills = ?, languages = ?, about = ?, password_hash = ?
                    WHERE id = ?
                """, (name, email, role, education, career_goal, skills, languages, about, pw_hash, user_id))
            else:
                cursor.execute("""
                    UPDATE users
                    SET name = ?, email = ?, role = ?, education = ?, career_goal = ?,
                        skills = ?, languages = ?, about = ?
                    WHERE id = ?
                """, (name, email, role, education, career_goal, skills, languages, about, user_id))

            connection.commit()
            flash(f"User '{name}' updated successfully.", "success")
            return redirect(url_for("admin_users"))

        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        if not user:
            flash("User not found.", "error")
            return redirect(url_for("admin_users"))
    finally:
        connection.close()

    return render_template("admin/user_edit.html", user=user)


@app.route("/admin/users/<int:user_id>/delete", methods=["POST"])
@admin_required
def admin_delete_user(user_id):
    if user_id == session.get("user_id"):
        flash("You cannot delete your own logged-in admin account.", "error")
        return redirect(url_for("admin_users"))

    connection = sqlite3.connect(DATABASE)
    try:
        cursor = connection.cursor()
        cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        connection.commit()
        flash("User account deleted successfully.", "info")
    finally:
        connection.close()

    return redirect(url_for("admin_users"))


@app.route("/admin/careers")
@admin_required
def admin_careers():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row

    try:
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM careers ORDER BY name ASC")
        careers = cursor.fetchall()

        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM careers")
        total_careers = cursor.fetchone()[0]
        stats = {"total_users": total_users, "total_careers": total_careers}
    finally:
        connection.close()

    return render_template("admin/careers.html", careers=careers, stats=stats)


@app.route("/admin/careers/add", methods=["GET", "POST"])
@admin_required
def admin_add_career():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        reason = request.form.get("reason", "").strip()
        entry_salary = request.form.get("entry_salary", "").strip()
        exp_salary = request.form.get("exp_salary", "").strip()

        skills_raw = [s.strip() for s in request.form.get("skills", "").split(",") if s.strip()]
        roles_raw = [r.strip() for r in request.form.get("roles", "").split(",") if r.strip()]
        growth_raw = [g.strip() for g in request.form.get("growth", "").split(",") if g.strip()]
        roadmap_raw = [line.strip() for line in request.form.get("roadmap", "").splitlines() if line.strip()]
        projects_raw = [line.strip() for line in request.form.get("projects", "").splitlines() if line.strip()]

        connection = sqlite3.connect(DATABASE)
        try:
            cursor = connection.cursor()
            cursor.execute("""
                INSERT INTO careers 
                (name, description, reason, entry_salary, exp_salary, skills, roles, growth, roadmap, projects, resources)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                name,
                description,
                reason,
                entry_salary,
                exp_salary,
                json.dumps(skills_raw, ensure_ascii=False),
                json.dumps(roles_raw, ensure_ascii=False),
                json.dumps(growth_raw, ensure_ascii=False),
                json.dumps(roadmap_raw, ensure_ascii=False),
                json.dumps(projects_raw, ensure_ascii=False),
                json.dumps(["Official documentation", "GitHub", "Online courses"], ensure_ascii=False)
            ))
            connection.commit()
            load_careers_from_db()
            flash(f"Career track '{name}' was added successfully!", "success")
            return redirect(url_for("admin_careers"))
        except sqlite3.IntegrityError:
            flash(f"A career named '{name}' already exists.", "error")
        finally:
            connection.close()

    return render_template("admin/career_form.html", career=None)


@app.route("/admin/careers/<int:career_id>/edit", methods=["GET", "POST"])
@admin_required
def admin_edit_career(career_id):
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row

    try:
        cursor = connection.cursor()

        if request.method == "POST":
            name = request.form.get("name", "").strip()
            description = request.form.get("description", "").strip()
            reason = request.form.get("reason", "").strip()
            entry_salary = request.form.get("entry_salary", "").strip()
            exp_salary = request.form.get("exp_salary", "").strip()

            skills_raw = [s.strip() for s in request.form.get("skills", "").split(",") if s.strip()]
            roles_raw = [r.strip() for r in request.form.get("roles", "").split(",") if r.strip()]
            growth_raw = [g.strip() for g in request.form.get("growth", "").split(",") if g.strip()]
            roadmap_raw = [line.strip() for line in request.form.get("roadmap", "").splitlines() if line.strip()]
            projects_raw = [line.strip() for line in request.form.get("projects", "").splitlines() if line.strip()]

            cursor.execute("""
                UPDATE careers
                SET name = ?, description = ?, reason = ?, entry_salary = ?, exp_salary = ?,
                    skills = ?, roles = ?, growth = ?, roadmap = ?, projects = ?
                WHERE id = ?
            """, (
                name,
                description,
                reason,
                entry_salary,
                exp_salary,
                json.dumps(skills_raw, ensure_ascii=False),
                json.dumps(roles_raw, ensure_ascii=False),
                json.dumps(growth_raw, ensure_ascii=False),
                json.dumps(roadmap_raw, ensure_ascii=False),
                json.dumps(projects_raw, ensure_ascii=False),
                career_id
            ))
            connection.commit()
            load_careers_from_db()
            flash(f"Career '{name}' updated successfully!", "success")
            return redirect(url_for("admin_careers"))

        cursor.execute("SELECT * FROM careers WHERE id = ?", (career_id,))
        career = cursor.fetchone()
        if not career:
            flash("Career track not found.", "error")
            return redirect(url_for("admin_careers"))

        skills_list = json.loads(career["skills"]) if career["skills"] else []
        roles_list = json.loads(career["roles"]) if career["roles"] else []
        growth_list = json.loads(career["growth"]) if career["growth"] else []
        roadmap_list = json.loads(career["roadmap"]) if career["roadmap"] else []
        projects_list = json.loads(career["projects"]) if career["projects"] else []

        context = {
            "career": career,
            "skills_str": ", ".join(skills_list),
            "roles_str": ", ".join(roles_list),
            "growth_str": ", ".join(growth_list),
            "roadmap_str": "\n".join(roadmap_list),
            "projects_str": "\n".join(projects_list)
        }
    finally:
        connection.close()

    return render_template("admin/career_form.html", **context)


@app.route("/admin/careers/<int:career_id>/delete", methods=["POST"])
@admin_required
def admin_delete_career(career_id):
    connection = sqlite3.connect(DATABASE)
    try:
        cursor = connection.cursor()
        cursor.execute("DELETE FROM careers WHERE id = ?", (career_id,))
        connection.commit()
        load_careers_from_db()
        flash("Career track deleted successfully.", "info")
    finally:
        connection.close()

    return redirect(url_for("admin_careers"))


@app.route("/admin/history")
@admin_required
def admin_history():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row

    try:
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM history ORDER BY id DESC")
        history_rows = cursor.fetchall()

        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM careers")
        total_careers = cursor.fetchone()[0]
        stats = {"total_users": total_users, "total_careers": total_careers}
    finally:
        connection.close()

    return render_template("admin/history.html", history=history_rows, stats=stats)


@app.route("/admin/history/<int:log_id>/delete", methods=["POST"])
@admin_required
def admin_delete_log(log_id):
    connection = sqlite3.connect(DATABASE)
    try:
        cursor = connection.cursor()
        cursor.execute("DELETE FROM history WHERE id = ?", (log_id,))
        connection.commit()
        flash("Prediction log record deleted.", "info")
    finally:
        connection.close()

    return redirect(url_for("admin_history"))


# =========================================================
# FILE SIZE ERROR
# =========================================================

@app.errorhandler(413)
def file_too_large(error):
    return render_template(
        "resume.html",
        error="The uploaded file is too large. Maximum size is 5 MB."
    ), 413


# =========================================================
# RUN APPLICATION
# =========================================================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
