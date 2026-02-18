from flask import Flask, render_template, request, Response
import os
import hashlib
import pdfplumber
import docx
import spacy
import re
import sqlite3
import csv
import io

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = "uploads"

nlp = spacy.load("en_core_web_sm")

# SKILL CATEGORIES
SKILL_CATEGORIES = {
    "oop_language": {
        "default_points": 20,
        "skills": ["python", "java", "c++", "javascript", "c#", "php"]
    },
    "web_design": {
        "default_points": 20,
        "skills": ["html", "css", "bootstrap"]
    },
    "database": {
        "default_points": 20,
        "skills": ["sql", "mysql", "postgresql", "mongodb"]
    }
}

# DATABASE
def init_db():
    conn = sqlite3.connect("applicants.db")
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS applicants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT,
        phone TEXT,
        skills TEXT,
        score REAL,
        decision TEXT,
        resume_path TEXT,
        file_hash TEXT UNIQUE
    )
    """)

    conn.commit()
    conn.close()

# FILE HASH (duplicate detection)
def get_file_hash(file_path):
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()

def is_duplicate(file_hash):
    conn = sqlite3.connect("applicants.db")
    c = conn.cursor()
    c.execute("SELECT id FROM applicants WHERE file_hash = ?", (file_hash,))
    row = c.fetchone()
    conn.close()
    return row is not None

# TEXT EXTRACTION
def extract_text(file_path):
    text = ""

    if file_path.endswith(".pdf"):
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""

    elif file_path.endswith(".docx"):
        doc = docx.Document(file_path)
        for para in doc.paragraphs:
            text += para.text

    return text.lower()

# CONTACT EXTRACTION
def extract_contact_details(text):
    email = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
    phone = re.search(r"(\+?\d[\d\s-]{8,15})", text)

    doc = nlp(text)
    name = None

    for ent in doc.ents:
        if ent.label_ == "PERSON":
            name = ent.text
            break

    return (
        name if name else "Not Found",
        email.group() if email else "Not Found",
        phone.group() if phone else "Not Found"
    )

# SKILL EXTRACTION
def extract_skills(text):
    found = []

    for category in SKILL_CATEGORIES.values():
        for skill in category["skills"]:
            if re.search(r"\b" + re.escape(skill) + r"\b", text):
                found.append(skill)

    return list(set(found))

# SCORING
def calculate_score(found_skills):
    score = 0
    bonus = 0
    oop_found = False

    for name, category in SKILL_CATEGORIES.items():
        matched = [s for s in found_skills if s in category["skills"]]

        if matched:
            score += category["default_points"]

            if name == "oop_language":
                oop_found = True

            if len(matched) > 1:
                bonus += (len(matched) - 1) * 5

    return score + bonus, oop_found

# SAVE TO DATABASE
def save_to_db(name, email, phone, skills, score, decision, path, file_hash):
    conn = sqlite3.connect("applicants.db")
    c = conn.cursor()

    c.execute("""
        INSERT INTO applicants
        (name, email, phone, skills, score, decision, resume_path, file_hash)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (name, email, phone, ", ".join(skills), score, decision, path, file_hash))

    conn.commit()
    conn.close()

# GET RANKINGS
def get_rankings():
    conn = sqlite3.connect("applicants.db")
    c = conn.cursor()

    c.execute("""
        SELECT name, email, phone, skills, score, decision
        FROM applicants
        ORDER BY score DESC
    """)

    rows = c.fetchall()
    conn.close()

    ranking = []
    for row in rows:
        ranking.append({
            "name":     row[0],
            "email":    row[1],
            "phone":    row[2],
            "skills":   row[3],
            "score":    row[4],
            "decision": row[5]
        })

    return ranking

# ROUTE
@app.route("/", methods=["GET", "POST"])
def index():

    result    = None
    duplicate = False
    ranking   = get_rankings()

    if request.method == "POST":
        file = request.files["resume"]

        if file:
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
            file.save(filepath)

            # --- Duplicate check ---
            file_hash = get_file_hash(filepath)

            if is_duplicate(file_hash):
                os.remove(filepath)
                duplicate = True
                return render_template("index.html",
                                       result=None,
                                       duplicate=duplicate,
                                       ranking=ranking)

            # --- Process resume ---
            text = extract_text(filepath)
            name, email, phone = extract_contact_details(text)
            skills = extract_skills(text)

            score, oop_found = calculate_score(skills)

            if not oop_found:
                decision = "Screening Requirement Not Met: Rejected"
                status   = "fail"
                score    = 0
            else:
                if score >= 60:
                    decision = "Proceed to Interview"
                    status   = "pass"
                else:
                    decision = "Screening Requirement Not Met: Rejected"
                    status   = "fail"

            save_to_db(name, email, phone, skills, score, decision, filepath, file_hash)

            # Refresh rankings after saving
            ranking = get_rankings()

            result = {
                "name":     name,
                "email":    email,
                "phone":    phone,
                "skills":   skills,
                "score":    score,
                "decision": decision,
                "status":   status
            }

    return render_template("index.html",
                           result=result,
                           duplicate=duplicate,
                           ranking=ranking)


# EXPORT ROUTE
@app.route("/export")
def export():
    conn = sqlite3.connect("applicants.db")
    c = conn.cursor()

    c.execute("""
        SELECT name, email, phone, skills, score, decision
        FROM applicants
        ORDER BY score DESC
    """)

    rows = c.fetchall()
    conn.close()

    # Build CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Header row
    writer.writerow(["Name", "Email", "Phone", "Skills", "Score", "Decision"])

    # Data rows
    for row in rows:
        writer.writerow(row)

    output.seek(0)

    return Response(
        output,
        mimetype="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=applicants.csv"
        }
    )


# ── Runs on startup (required for Render/gunicorn) ──
os.makedirs("uploads", exist_ok=True)
init_db()

if __name__ == "__main__":
    app.run(debug=True)