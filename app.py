import os
import sqlite3
import subprocess
from datetime import datetime
from functools import wraps

from flask import Flask, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, "therepy.db")
DEFAULT_MODEL = os.getenv("THERAPY_MODEL", "llama3.2:3b")
SECRET_KEY = os.getenv("THERAPY_SECRET_KEY", "change-this-before-deploying")
CONTEXT_MESSAGE_LIMIT = 12

SYSTEM_PROMPT = """You are Dr. Sarah, a warm, empathetic, and highly skilled therapist with 15 years of experience.

Core principles:
- Always prioritize the client's emotional well-being.
- Use active listening, validation, and thoughtful open-ended questions.
- Reflect back what you hear to show understanding.
- Maintain appropriate therapeutic boundaries.
- Use evidence-based techniques like CBT and mindfulness where appropriate.
- Encourage professional help for serious mental health concerns.
- You are not providing medical advice or a diagnosis.

Communication style:
- Speak naturally and conversationally, not clinically.
- Be warm, emotionally attuned, and non-judgmental.
- Give complete but concise responses.
- Help the client explore their own insights and next steps.
"""

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS chat_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    model_name TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_session_id INTEGER NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    emotional_state TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (chat_session_id) REFERENCES chat_sessions(id)
);
"""

app = Flask(__name__)
app.config["SECRET_KEY"] = SECRET_KEY
app.config["DATABASE_PATH"] = DATABASE_PATH
app.config["MODEL_NAME"] = DEFAULT_MODEL


class OllamaTherapist:
    def __init__(self, model_name: str):
        self.model_name = model_name

    def detect_emotional_state(self, message: str) -> str:
        emotional_indicators = {
            "anxious": ["worried", "nervous", "anxious", "scared", "panic", "stress", "overwhelmed"],
            "depressed": ["sad", "hopeless", "empty", "worthless", "tired", "exhausted", "down"],
            "angry": ["angry", "furious", "frustrated", "irritated", "mad", "rage", "annoyed"],
            "confused": ["confused", "lost", "uncertain", "don't know", "unclear", "mixed up"],
            "excited": ["excited", "happy", "thrilled", "amazing", "wonderful", "great", "fantastic"],
            "calm": ["peaceful", "relaxed", "calm", "content", "okay", "fine", "stable"],
        }

        message_lower = message.lower()
        for emotion, indicators in emotional_indicators.items():
            if any(indicator in message_lower for indicator in indicators):
                return emotion
        return "neutral"

    def build_prompt(self, messages: list[sqlite3.Row], emotional_state: str) -> str:
        context_lines = []
        for message in messages[-CONTEXT_MESSAGE_LIMIT:]:
            speaker = "Client" if message["role"] == "user" else "Dr. Sarah"
            context_lines.append(f"{speaker}: {message['content']}")

        emotional_hint = ""
        if emotional_state != "neutral":
            emotional_hint = (
                f"\nThe client's current emotional state appears to be {emotional_state}. "
                "Respond with appropriate empathy.\n"
            )

        context_block = "\n".join(context_lines)
        return (
            f"{SYSTEM_PROMPT}\n"
            "Keep the conversation private, supportive, and grounded in the context below.\n"
            f"{emotional_hint}\n"
            "Conversation so far:\n"
            f"{context_block}\n\n"
            "Continue the conversation as Dr. Sarah."
        )

    def generate_response(self, messages: list[sqlite3.Row], emotional_state: str) -> str:
        prompt = self.build_prompt(messages, emotional_state)

        try:
            result = subprocess.run(
                ["ollama", "run", self.model_name],
                input=prompt,
                capture_output=True,
                text=True,
                timeout=180,
                encoding="utf-8",
                errors="replace",
            )
        except FileNotFoundError:
            return (
                "I cannot reach Ollama right now. Please install Ollama on the Raspberry Pi and "
                f"pull the configured model '{self.model_name}'."
            )
        except subprocess.TimeoutExpired:
            return "I'm taking a little longer to think than usual. Please try sending that again."
        except Exception:
            return "I'm having some technical difficulty right now, but I'm still here with you."

        if result.returncode != 0:
            error_text = (result.stderr or "").strip()
            if "pull" in error_text.lower() or "not found" in error_text.lower():
                return (
                    f"The configured model '{self.model_name}' is not installed yet. "
                    f"Run `ollama pull {self.model_name}` on the Raspberry Pi."
                )
            return "I'm having some technical difficulty right now, but I'm still here with you."

        response = (result.stdout or "").strip()
        if response.startswith("Dr. Sarah:"):
            response = response[len("Dr. Sarah:") :].strip()
        return response or "I'm here with you. Can you tell me a little more about that?"


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = sqlite3.connect(app.config["DATABASE_PATH"])
        g.db.row_factory = sqlite3.Row
    return g.db


def init_db() -> None:
    db = sqlite3.connect(app.config["DATABASE_PATH"])
    try:
        db.executescript(SCHEMA)
        db.commit()
    finally:
        db.close()


@app.teardown_appcontext
def close_db(exception):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def login_required(view):
    @wraps(view)
    def wrapped_view(**kwargs):
        if not current_user():
            return redirect(url_for("login"))
        return view(**kwargs)

    return wrapped_view


def current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None

    db = get_db()
    return db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


def create_chat_session(user_id: int, title: str = "New chat") -> int:
    db = get_db()
    now = datetime.utcnow().isoformat()
    cursor = db.execute(
        """
        INSERT INTO chat_sessions (user_id, title, model_name, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (user_id, title, app.config["MODEL_NAME"], now, now),
    )
    db.commit()
    return cursor.lastrowid


def get_user_sessions(user_id: int) -> list[sqlite3.Row]:
    db = get_db()
    return db.execute(
        """
        SELECT *
        FROM chat_sessions
        WHERE user_id = ?
        ORDER BY updated_at DESC, id DESC
        """,
        (user_id,),
    ).fetchall()


def get_session_or_404(session_id: int, user_id: int):
    db = get_db()
    chat_session = db.execute(
        "SELECT * FROM chat_sessions WHERE id = ? AND user_id = ?",
        (session_id, user_id),
    ).fetchone()
    return chat_session


def get_session_messages(session_id: int) -> list[sqlite3.Row]:
    db = get_db()
    return db.execute(
        """
        SELECT *
        FROM messages
        WHERE chat_session_id = ?
        ORDER BY id ASC
        """,
        (session_id,),
    ).fetchall()


def add_message(chat_session_id: int, role: str, content: str, emotional_state: str | None = None) -> None:
    db = get_db()
    now = datetime.utcnow().isoformat()
    db.execute(
        """
        INSERT INTO messages (chat_session_id, role, content, emotional_state, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (chat_session_id, role, content, emotional_state, now),
    )
    db.execute(
        "UPDATE chat_sessions SET updated_at = ? WHERE id = ?",
        (now, chat_session_id),
    )
    db.commit()


def maybe_update_chat_title(chat_session_id: int, content: str) -> None:
    db = get_db()
    chat_session = db.execute(
        "SELECT title FROM chat_sessions WHERE id = ?",
        (chat_session_id,),
    ).fetchone()
    if not chat_session or chat_session["title"] != "New chat":
        return

    title = " ".join(content.split())
    title = title[:60].strip() or "New chat"
    db.execute(
        "UPDATE chat_sessions SET title = ? WHERE id = ?",
        (title, chat_session_id),
    )
    db.commit()


@app.context_processor
def inject_template_context():
    return {
        "auth_user": current_user(),
        "model_name": app.config["MODEL_NAME"],
    }


@app.route("/")
def index():
    user = current_user()
    if not user:
        return redirect(url_for("login"))

    sessions = get_user_sessions(user["id"])
    if sessions:
        return redirect(url_for("chat", session_id=sessions[0]["id"]))

    new_session_id = create_chat_session(user["id"])
    return redirect(url_for("chat", session_id=new_session_id))


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if current_user():
        return redirect(url_for("index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if len(username) < 3:
            flash("Username must be at least 3 characters long.", "error")
        elif len(password) < 8:
            flash("Password must be at least 8 characters long.", "error")
        elif password != confirm_password:
            flash("Passwords do not match.", "error")
        else:
            db = get_db()
            existing_user = db.execute(
                "SELECT id FROM users WHERE username = ?",
                (username,),
            ).fetchone()
            if existing_user:
                flash("That username is already taken.", "error")
            else:
                db.execute(
                    "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
                    (username, generate_password_hash(password), datetime.utcnow().isoformat()),
                )
                db.commit()
                flash("Account created. Please log in.", "success")
                return redirect(url_for("login"))

    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user():
        return redirect(url_for("index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        db = get_db()
        user = db.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,),
        ).fetchone()

        if not user or not check_password_hash(user["password_hash"], password):
            flash("Invalid username or password.", "error")
        else:
            session.clear()
            session["user_id"] = user["id"]
            return redirect(url_for("index"))

    return render_template("login.html")


@app.route("/logout", methods=["POST"])
@login_required
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))


@app.route("/chat/new", methods=["POST"])
@login_required
def new_chat():
    user = current_user()
    session_id = create_chat_session(user["id"])
    return redirect(url_for("chat", session_id=session_id))


@app.route("/chat/<int:session_id>")
@login_required
def chat(session_id: int):
    user = current_user()
    chat_session = get_session_or_404(session_id, user["id"])
    if not chat_session:
        flash("Chat session not found.", "error")
        return redirect(url_for("index"))

    sessions = get_user_sessions(user["id"])
    messages = get_session_messages(session_id)
    return render_template(
        "chat.html",
        chat_session=chat_session,
        sessions=sessions,
        messages=messages,
    )


@app.route("/chat/<int:session_id>/message", methods=["POST"])
@login_required
def send_message(session_id: int):
    user = current_user()
    chat_session = get_session_or_404(session_id, user["id"])
    if not chat_session:
        flash("Chat session not found.", "error")
        return redirect(url_for("index"))

    user_message = request.form.get("message", "").strip()
    if not user_message:
        flash("Please enter a message before sending.", "error")
        return redirect(url_for("chat", session_id=session_id))

    therapist = OllamaTherapist(chat_session["model_name"])
    emotional_state = therapist.detect_emotional_state(user_message)

    add_message(session_id, "user", user_message, emotional_state)
    maybe_update_chat_title(session_id, user_message)

    message_history = get_session_messages(session_id)
    assistant_response = therapist.generate_response(message_history, emotional_state)
    add_message(session_id, "assistant", assistant_response)

    return redirect(url_for("chat", session_id=session_id))


init_db()


if __name__ == "__main__":
    host = os.getenv("THERAPY_HOST", "0.0.0.0")
    port = int(os.getenv("THERAPY_PORT", "8000"))
    app.run(host=host, port=port, debug=False)
