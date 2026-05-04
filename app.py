import sqlite3
import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import json
from PyPDF2 import PdfReader

def init_db():
    conn = sqlite3.connect("quiz.db")
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT,
        name TEXT,
        score INTEGER
    )
    """)

    conn.commit()
    conn.close()
init_db()
app = Flask(__name__)
CORS(app)
quiz_results={}
@app.route("/generate", methods=["POST"])
def generate_quiz():

    # =========================
    # HANDLE PDF INPUT
    # =========================
    if 'file' in request.files:
        file = request.files['file']

        reader = PdfReader(file)
        content = ""

        for page in reader.pages:
            text = page.extract_text()
            if text:
                content += text + "\n"

        difficulty = request.form.get("difficulty", "medium")
        num = request.form.get("num", 5)

    # =========================
    # HANDLE JSON INPUT
    # =========================
    else:
        data = request.get_json(force=True)

        difficulty = data.get("difficulty", "medium")
        num = data.get("num", 5)

        if data["type"] == "text":
            content = data["content"]

        elif data["type"] == "subject":
            subject = data["subject"]

            subjects = {
                "os": "Operating System concepts: process, threads, scheduling, deadlocks, memory management",
                "dbms": "DBMS concepts: normalization, SQL, transactions, indexing",
                "ddco": "Computer Organization: CPU, memory hierarchy, instruction cycle"
            }

            content = subjects.get(subject, "")

    # =========================
    # PROMPT
    # =========================
    prompt = f"""
Generate exactly {num} {difficulty} level multiple choice questions ONLY from the following content:

{content}

Return STRICT JSON only:

[
  {{
    "question": "string",
    "options": ["A", "B", "C", "D"],
    "answer": 0,
    "explanation": "short explanation"
  }}
]

Rules:
- No extra text
- Questions must come ONLY from given content
- Difficulty must match: {difficulty}
"""

    api_key = os.environ.get("API_KEY")
    

    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        json={
            "model": "llama-3.1-8b-instant",
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
    )

    result = response.json()
    print("API Response:", result)

    if "choices" not in result:
        return jsonify({"error": result})

    ai_text = result["choices"][0]["message"]["content"]

    try:
        parsed = json.loads(ai_text)
        clean_json = json.dumps(parsed)
    except:
        clean_json = ai_text

    return jsonify({"data": clean_json})

@app.route("/submit_result", methods=["POST"])
def submit_result():
    data = request.get_json()

    code = data["code"]
    name = data["name"]
    score = data["score"]

    conn = sqlite3.connect("quiz.db")
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO results (code, name, score) VALUES (?, ?, ?)",
        (code, name, score)
    )

    conn.commit()
    conn.close()
    print("Received:",data)
    return jsonify({"message": "saved"})
@app.route("/get_results/<code>")
def get_results(code):
    conn = sqlite3.connect("quiz.db")
    cursor = conn.cursor()

    cursor.execute("SELECT name, score FROM results WHERE code = ?", (code,))
    rows = cursor.fetchall()

    conn.close()

    result = [{"name": r[0], "score": r[1]} for r in rows]

    return jsonify(result)


if __name__ == "__main__":
    app.run(host="0.0.0.0",port=10000)