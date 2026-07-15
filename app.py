from flask import Flask, render_template, request, session,redirect
from google import genai
from flask import Flask, render_template, request, session, redirect
from google import genai
from authlib.integrations.flask_client import OAuth
import re
from groq import Groq
app = Flask(__name__)
app.secret_key = "mysecretkey"
oauth = OAuth(app)
import os

google = oauth.register(
    name='google',
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile'
    }
)

client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/login')
def login():
    return render_template('index.html')


@app.route('/login', methods=['POST'])
def login_user():

    name = request.form.get("name")
    

    print("Name:", name)
  

    session["name"] = name
   

    return redirect("/skill")


@app.route('/skill')
def skill():
    return render_template('skill.html')


@app.route('/interview', methods=['POST'])
def interview():

    skill = request.form.get('skill')

    try:
        # Gemini first
        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=f"""
Generate 5 short {skill} interview questions.
Return only the questions.
One question per line.
"""
        )

        text = response.text

    except Exception as e:

        print("Gemini failed:", e)
        print("Using Groq...")

        try:
            groq_response = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {
                        "role": "user",
                        "content": f"""
Generate 5 short {skill} interview questions.
Return only the questions.
One question per line.
"""
                    }
                ]
            )

            text = groq_response.choices[0].message.content

        except Exception as e:
            print("Groq failed:", e)

            return render_template(
                "interview.html",
                question="",
                current=0,
                total=5,
                error="SK AI service is busy. Please try again."
            )

    questions = text.split("\n")
    questions = [q.strip() for q in questions if q.strip()]
    questions = questions[:5]
    print("TOTAL QUESTIONS GENERATED =", len(questions))
    print(questions)

    session["questions"] = questions
    session["current"] = 0
    session["answers"] = []

    return render_template(
        "interview.html",
        question=questions[0],
        current=0,
        total=len(questions)
    )

@app.route('/next', methods=['POST'])
def next_question():

    user_answer = request.form.get("answer")

    # STEP 1: create answers list if not exists
    if "answers" not in session:
        session["answers"] = []

    answers = session["answers"]

    # STEP 2: store current answer
    answers.append(user_answer)
    session["answers"] = answers

    # STEP 3: move to next question
    current = session.get("current", 0)
    current += 1
    session["current"] = current

    questions = session.get("questions", [])

    # STEP 4: if finished → go to evaluate
    if current >= len(questions):
        return redirect("/evaluate")

    return render_template(
        "interview.html",
        question=questions[current],
        current=current,
        total=len(questions)
    )
@app.route("/evaluate", methods=["POST", "GET"])
def evaluate():

    questions = session.get("questions", [])
    answers = session.get("answers", [])

    # Save final answer if coming from submit button
    user_answer = request.form.get("answer")

    if user_answer is not None:
        if len(answers) < len(questions):
            answers.append(user_answer)
            session["answers"] = answers

    questions = session.get("questions", [])
    answers = session.get("answers", [])

    print("QUESTIONS =", len(questions))
    print("ANSWERS =", len(answers))

    results = []
    total_score = 0

    # Loop through all questions safely
    for i in range(min(len(questions), len(answers))):

        question = questions[i]
        answer = answers[i]

        prompt = f"""
You are an expert AI interview evaluator.

Question:
{question}

Candidate Answer:
{answer}

Return format:

Score: XX/20
Ideal Answer: short
Feedback: short
"""

        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash-lite",
                contents=prompt
            )

            ai_text = response.text

        except Exception as e:

            print("Gemini evaluation failed:", e)

            try:
                groq_response = groq_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                )

                ai_text = groq_response.choices[0].message.content

            except Exception as e:

                print("Groq evaluation failed:", e)

                ai_text = """
Score: 0/20
Ideal Answer: N/A
Feedback: AI service unavailable.
"""

        match = re.search(r"Score:\s*(\d+)", ai_text)
        score = int(match.group(1)) if match else 0

        total_score += score

        results.append({
            "question": question,
            "user_answer": answer,
            "ai_result": ai_text,
            "score": score
        })

    return render_template(
        "result.html",
        results=results,
        total_score=total_score
    )
@app.route('/google-login')
def google_login():
    return google.authorize_redirect(
        redirect_uri="https://tech-talent-ai-interview.onrender.com/callback"
    )
    # ADD STEP 8 HERE
@app.route('/callback')
def callback():

    token = google.authorize_access_token()

    user = token['userinfo']

    session["name"] = user["name"]
    session["email"] = user["email"]

    return redirect("/skill")
if __name__ == '__main__':
    app.run(debug=True)