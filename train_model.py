from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
import joblib

# ==================================================
# EXPANDED TRAINING DATA
# ==================================================

data = {
    "text": [
        # Python Developer
        "python coding programming backend automation scripting",
        "python software development django flask fastapi",
        "python backend coding automation scripts rest api",
        "python developer oop data structures algorithms sql",
        "backend python developer web services celery redis",

        # Java Developer
        "java backend android software programming spring boot",
        "java application backend development hibernate microservices",
        "java enterprise software programming maven gradle jpa",
        "core java developer oop collections multithreading sql",
        "java spring backend engineer api development",

        # C/C++ Developer
        "c c++ systems programming software memory management",
        "c++ systems developer programming embedded linux",
        "c programming system software compilers performance",
        "low level c c++ developer operating systems algorithms",
        "c++ game development graphics directx opengl",

        # Web Developer
        "html css javascript web website development responsive",
        "website html css javascript bootstrap dom frontend",
        "web development frontend javascript jquery css3 flexbox",
        "web designer developer html5 css3 modern websites",
        "frontend web developer responsive ui dynamic pages",

        # Frontend Developer
        "frontend html css javascript react ui components redux",
        "frontend website design javascript vue angular typescript",
        "react frontend ui development state management next.js",
        "client side web applications react redux tailwind responsive",
        "frontend engineer single page applications javascript vue",

        # Full Stack Developer
        "full stack frontend backend html css javascript node sql react",
        "full stack web development frontend backend express mongodb",
        "web backend frontend database development mern stack mean",
        "full stack engineer node.js react postgresql api",
        "end to end web application development frontend backend database",

        # Data Analyst
        "data analysis excel statistics business data power bi tableau",
        "data analyst sql excel analytics reporting dashboards",
        "data reporting visualization business analysis sql queries",
        "exploratory data analysis statistical analysis metrics kpis",
        "business intelligence data cleaning reporting charts insights",

        # Data Scientist
        "data science machine learning ai python data deep learning",
        "machine learning python prediction artificial intelligence models",
        "ai data science python prediction pandas numpy scikit-learn",
        "nlp computer vision neural networks machine learning models",
        "data scientist predictive modeling statistical machine learning",

        # Database Developer
        "database sql mysql data management queries schema design",
        "mysql sql database developer stored procedures postgresql",
        "database management sql data indexing optimization dbms",
        "relational database developer oracle sql server pl/sql",
        "sql query optimization database design normalization etl",

        # DevOps Engineer
        "devops linux cloud deployment server networking docker kubernetes",
        "devops git linux cloud aws ci/cd pipeline automation",
        "server deployment networking cloud infrastructure terraform bash",
        "site reliability engineer devops containerization docker monitoring",
        "cloud devops engineer automated deployment kubernetes aws azure",

        # UI/UX Designer
        "ui ux design creative figma photoshop user experience wireframes",
        "ui design figma user experience prototypes user interface",
        "ux creative design photoshop user research design systems",
        "product design ui ux interaction design mobile app design",
        "figma prototyping usability testing user flow wireframing",

        # Software Developer
        "software coding programming application development algorithms",
        "software developer programming java python problem solving",
        "application software development coding software architecture",
        "software engineering problem solving clean code debugging",
        "software engineer computer science fundamentals git agile"
    ],
    "career": [
        # Python Developer
        "Python Developer", "Python Developer", "Python Developer", "Python Developer", "Python Developer",
        # Java Developer
        "Java Developer", "Java Developer", "Java Developer", "Java Developer", "Java Developer",
        # C/C++ Developer
        "C/C++ Developer", "C/C++ Developer", "C/C++ Developer", "C/C++ Developer", "C/C++ Developer",
        # Web Developer
        "Web Developer", "Web Developer", "Web Developer", "Web Developer", "Web Developer",
        # Frontend Developer
        "Frontend Developer", "Frontend Developer", "Frontend Developer", "Frontend Developer", "Frontend Developer",
        # Full Stack Developer
        "Full Stack Developer", "Full Stack Developer", "Full Stack Developer", "Full Stack Developer", "Full Stack Developer",
        # Data Analyst
        "Data Analyst", "Data Analyst", "Data Analyst", "Data Analyst", "Data Analyst",
        # Data Scientist
        "Data Scientist", "Data Scientist", "Data Scientist", "Data Scientist", "Data Scientist",
        # Database Developer
        "Database Developer", "Database Developer", "Database Developer", "Database Developer", "Database Developer",
        # DevOps Engineer
        "DevOps Engineer", "DevOps Engineer", "DevOps Engineer", "DevOps Engineer", "DevOps Engineer",
        # UI/UX Designer
        "UI/UX Designer", "UI/UX Designer", "UI/UX Designer", "UI/UX Designer", "UI/UX Designer",
        # Software Developer
        "Software Developer", "Software Developer", "Software Developer", "Software Developer", "Software Developer"
    ]
}

# ==================================================
# ML PIPELINE
# ==================================================

model = Pipeline([
    ("tfidf", TfidfVectorizer(ngram_range=(1, 2))),
    ("classifier", LogisticRegression(max_iter=1000, C=1.0))
])

# ==================================================
# TRAIN MODEL
# ==================================================

print(f"Training on {len(data['text'])} examples across {len(set(data['career']))} careers...")
model.fit(data["text"], data["career"])
print("Machine Learning model trained successfully.")

# ==================================================
# SAVE MODEL (using joblib to match app.py)
# ==================================================

joblib.dump(model, "career_model.pkl")
print("Model saved cleanly as career_model.pkl with current scikit-learn version.")

# ==================================================
# TEST MODEL
# ==================================================

test_cases = [
    "python coding backend automation flask",
    "figma creative wireframing prototypes",
    "docker kubernetes linux aws cloud deployment",
    "excel sql data visualization business reporting",
    "react javascript frontend ui components"
]

print("\n--- Validation Tests ---")
for text in test_cases:
    pred = model.predict([text])[0]
    prob = max(model.predict_proba([text])[0]) * 100
    print(f"Input: '{text}' -> {pred} ({prob:.1f}%)")

print("\nML model training and verification complete!")
