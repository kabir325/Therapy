import os
import sqlite3
import subprocess
import threading
from datetime import datetime
from functools import wraps

from flask import Flask, g, jsonify, request, session
from werkzeug.security import check_password_hash, generate_password_hash


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, "therepy.db")
DEFAULT_MODEL = os.getenv("THERAPY_MODEL", "qwen2.5:1.5b")
SECRET_KEY = os.getenv("THERAPY_SECRET_KEY", "change-this-before-deploying")
ALLOWED_ORIGINS = {
    origin.strip()
    for origin in os.getenv(
        "THERAPY_ALLOWED_ORIGINS",
        "http://localhost:3005,http://127.0.0.1:3005",
    ).split(",")
    if origin.strip()
}
CONTEXT_MESSAGE_LIMIT = 8

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
- Keep responses supportive, grounded, and concise.
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
    status TEXT NOT NULL DEFAULT 'complete',
    created_at TEXT NOT NULL,
    updated_at TEXT,
    FOREIGN KEY (chat_session_id) REFERENCES chat_sessions(id)
);
"""

app = Flask(__name__)
app.config["SECRET_KEY"] = SECRET_KEY
app.config["DATABASE_PATH"] = DATABASE_PATH
app.config["MODEL_NAME"] = DEFAULT_MODEL
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.getenv("THERAPY_SECURE_COOKIE", "false").lower() == "true"


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
            "Keep the conversation supportive, practical, and grounded in the saved session context.\n"
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
                timeout=120,
                encoding="utf-8",
                errors="replace",
            )
        except FileNotFoundError:
            return (
                "I cannot reach Ollama right now. Please install Ollama on the Raspberry Pi and "
                f"pull the configured model '{self.model_name}'."
            )
        except subprocess.TimeoutExpired:
            return "I'm taking longer than usual to think. Please try again in a moment."
        except Exception:
            return "I'm having some technical difficulty right now, but I'm still here with you."

        if result.returncode != 0:
            error_text = (result.stderr or "").strip().lower()
            if "pull" in error_text or "not found" in error_text:
                return (
                    f"The configured model '{self.model_name}' is not installed yet. "
                    f"Run `ollama pull {self.model_name}` on the Raspberry Pi."
                )
            return "I'm having some technical difficulty right now, but I'm still here with you."

        response = (result.stdout or "").strip()
        if response.startswith("Dr. Sarah:"):
            response = response[len("Dr. Sarah:") :].strip()
        return response or "I'm here with you. Can you tell me a little more about that?"


def utc_now() -> str:
    return datetime.utcnow().isoformat()


def get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(app.config["DATABASE_PATH"], check_same_thread=False)
    connection.row_factory = sqlite3.Row
    return connection


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = get_connection()
    return g.db


def ensure_column(db: sqlite3.Connection, table_name: str, column_name: str, definition: str) -> None:
    columns = {row["name"] for row in db.execute(f"PRAGMA table_info({table_name})").fetchall()}
    if column_name not in columns:
        db.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")


def init_db() -> None:
    db = get_connection()
    try:
        db.executescript(SCHEMA)
        ensure_column(db, "messages", "status", "TEXT NOT NULL DEFAULT 'complete'")
        ensure_column(db, "messages", "updated_at", "TEXT")
        db.execute("UPDATE messages SET status = 'complete' WHERE status IS NULL OR status = ''")
        db.execute("UPDATE messages SET updated_at = created_at WHERE updated_at IS NULL")
        db.commit()
    finally:
        db.close()


@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        return ("", 204)
    return None


@app.after_request
def add_cors_headers(response):
    origin = request.headers.get("Origin")
    if origin and origin in ALLOWED_ORIGINS:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        response.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
        response.headers["Vary"] = "Origin"
    return response


@app.teardown_appcontext
def close_db(exception):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def json_error(message: str, status_code: int):
    response = jsonify({"error": message})
    response.status_code = status_code
    return response


def current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None

    db = get_db()
    return db.execute("SELECT id, username, created_at FROM users WHERE id = ?", (user_id,)).fetchone()


def api_login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        user = current_user()
        if not user:
            return json_error("Authentication required.", 401)
        return view(*args, **kwargs)

    return wrapped_view


def serialize_user(user: sqlite3.Row) -> dict:
    return {
        "id": user["id"],
        "username": user["username"],
        "createdAt": user["created_at"],
    }


def serialize_message(message: sqlite3.Row) -> dict:
    return {
        "id": message["id"],
        "role": message["role"],
        "content": message["content"],
        "status": message["status"],
        "emotionalState": message["emotional_state"],
        "createdAt": message["created_at"],
        "updatedAt": message["updated_at"],
    }


def serialize_chat_session(chat_session: sqlite3.Row) -> dict:
    return {
        "id": chat_session["id"],
        "title": chat_session["title"],
        "modelName": chat_session["model_name"],
        "createdAt": chat_session["created_at"],
        "updatedAt": chat_session["updated_at"],
        "lastMessage": chat_session["last_message"],
    }


def get_session_for_user(db: sqlite3.Connection, session_id: int, user_id: int):
    return db.execute(
        """
        SELECT *
        FROM chat_sessions
        WHERE id = ? AND user_id = ?
        """,
        (session_id, user_id),
    ).fetchone()


def get_user_sessions(db: sqlite3.Connection, user_id: int) -> list[sqlite3.Row]:
    return db.execute(
        """
        SELECT
            s.*,
            COALESCE(
                (
                    SELECT content
                    FROM messages m
                    WHERE m.chat_session_id = s.id
                    ORDER BY m.id DESC
                    LIMIT 1
                ),
                ''
            ) AS last_message
        FROM chat_sessions s
        WHERE s.user_id = ?
        ORDER BY s.updated_at DESC, s.id DESC
        """,
        (user_id,),
    ).fetchall()


def get_session_messages(db: sqlite3.Connection, session_id: int) -> list[sqlite3.Row]:
    return db.execute(
        """
        SELECT *
        FROM messages
        WHERE chat_session_id = ?
        ORDER BY id ASC
        """,
        (session_id,),
    ).fetchall()


def create_chat_session(db: sqlite3.Connection, user_id: int, title: str = "New chat") -> sqlite3.Row:
    now = utc_now()
    cursor = db.execute(
        """
        INSERT INTO chat_sessions (user_id, title, model_name, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (user_id, title, app.config["MODEL_NAME"], now, now),
    )
    db.commit()
    session_id = cursor.lastrowid
    return db.execute(
        "SELECT *, '' AS last_message FROM chat_sessions WHERE id = ?",
        (session_id,),
    ).fetchone()


def maybe_update_chat_title(db: sqlite3.Connection, chat_session_id: int, content: str) -> None:
    chat_session = db.execute(
        "SELECT title FROM chat_sessions WHERE id = ?",
        (chat_session_id,),
    ).fetchone()
    if not chat_session or chat_session["title"] != "New chat":
        return

    title = " ".join(content.split())
    title = title[:60].strip() or "New chat"
    db.execute(
        "UPDATE chat_sessions SET title = ?, updated_at = ? WHERE id = ?",
        (title, utc_now(), chat_session_id),
    )


def create_message(
    db: sqlite3.Connection,
    chat_session_id: int,
    role: str,
    content: str,
    emotional_state: str | None = None,
    status: str = "complete",
) -> sqlite3.Row:
    now = utc_now()
    cursor = db.execute(
        """
        INSERT INTO messages (chat_session_id, role, content, emotional_state, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (chat_session_id, role, content, emotional_state, status, now, now),
    )
    db.execute(
        "UPDATE chat_sessions SET updated_at = ? WHERE id = ?",
        (now, chat_session_id),
    )
    db.commit()
    return db.execute("SELECT * FROM messages WHERE id = ?", (cursor.lastrowid,)).fetchone()


def update_message_status(message_id: int, status: str, content: str) -> None:
    db = get_connection()
    try:
        now = utc_now()
        db.execute(
            "UPDATE messages SET status = ?, content = ?, updated_at = ? WHERE id = ?",
            (status, content, now, message_id),
        )
        message = db.execute("SELECT chat_session_id FROM messages WHERE id = ?", (message_id,)).fetchone()
        if message:
            db.execute(
                "UPDATE chat_sessions SET updated_at = ? WHERE id = ?",
                (now, message["chat_session_id"]),
            )
        db.commit()
    finally:
        db.close()


def generate_assistant_reply(chat_session_id: int, assistant_message_id: int, emotional_state: str) -> None:
    db = get_connection()
    try:
        chat_session = db.execute(
            "SELECT * FROM chat_sessions WHERE id = ?",
            (chat_session_id,),
        ).fetchone()
        if not chat_session:
            update_message_status(assistant_message_id, "error", "This chat session could not be found anymore.")
            return

        messages = db.execute(
            """
            SELECT *
            FROM messages
            WHERE chat_session_id = ? AND status = 'complete'
            ORDER BY id ASC
            """,
            (chat_session_id,),
        ).fetchall()
        therapist = OllamaTherapist(chat_session["model_name"])
        response = therapist.generate_response(messages, emotional_state)
        update_message_status(assistant_message_id, "complete", response)
    except Exception:
        update_message_status(
            assistant_message_id,
            "error",
            "I'm having some technical difficulty right now, but I'm still here with you.",
        )
    finally:
        db.close()


def has_pending_assistant_message(db: sqlite3.Connection, chat_session_id: int) -> bool:
    pending = db.execute(
        """
        SELECT id
        FROM messages
        WHERE chat_session_id = ? AND role = 'assistant' AND status = 'pending'
        LIMIT 1
        """,
        (chat_session_id,),
    ).fetchone()
    return pending is not None


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"ok": True, "modelName": app.config["MODEL_NAME"]})


@app.route("/api/auth/me", methods=["GET"])
def auth_me():
    user = current_user()
    if not user:
        return jsonify({"user": None})
    return jsonify({"user": serialize_user(user)})


@app.route("/api/auth/signup", methods=["POST"])
def signup():
    payload = request.get_json(silent=True) or {}
    username = str(payload.get("username", "")).strip()
    password = str(payload.get("password", ""))
    confirm_password = str(payload.get("confirmPassword", ""))

    if len(username) < 3:
        return json_error("Username must be at least 3 characters long.", 400)
    if len(password) < 8:
        return json_error("Password must be at least 8 characters long.", 400)
    if password != confirm_password:
        return json_error("Passwords do not match.", 400)

    db = get_db()
    existing_user = db.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
    if existing_user:
        return json_error("That username is already taken.", 409)

    now = utc_now()
    cursor = db.execute(
        "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
        (username, generate_password_hash(password), now),
    )
    db.commit()
    user = db.execute(
        "SELECT id, username, created_at FROM users WHERE id = ?",
        (cursor.lastrowid,),
    ).fetchone()
    session.clear()
    session["user_id"] = user["id"]
    return jsonify({"user": serialize_user(user)})


@app.route("/api/auth/login", methods=["POST"])
def login():
    payload = request.get_json(silent=True) or {}
    username = str(payload.get("username", "")).strip()
    password = str(payload.get("password", ""))

    db = get_db()
    user = db.execute(
        "SELECT * FROM users WHERE username = ?",
        (username,),
    ).fetchone()

    if not user or not check_password_hash(user["password_hash"], password):
        return json_error("Invalid username or password.", 401)

    session.clear()
    session["user_id"] = user["id"]
    return jsonify(
        {
            "user": {
                "id": user["id"],
                "username": user["username"],
                "createdAt": user["created_at"],
            }
        }
    )


@app.route("/api/auth/logout", methods=["POST"])
@api_login_required
def logout():
    session.clear()
    return jsonify({"ok": True})


@app.route("/api/chats", methods=["GET"])
@api_login_required
def list_chats():
    user = current_user()
    db = get_db()
    sessions = get_user_sessions(db, user["id"])
    return jsonify({"sessions": [serialize_chat_session(item) for item in sessions]})


@app.route("/api/chats", methods=["POST"])
@api_login_required
def create_chat():
    user = current_user()
    db = get_db()
    chat_session = create_chat_session(db, user["id"])
    return jsonify({"session": serialize_chat_session(chat_session)}), 201


@app.route("/api/chats/<int:session_id>", methods=["GET"])
@api_login_required
def get_chat(session_id: int):
    user = current_user()
    db = get_db()
    chat_session = get_session_for_user(db, session_id, user["id"])
    if not chat_session:
        return json_error("Chat session not found.", 404)

    enriched_session = db.execute(
        """
        SELECT
            s.*,
            COALESCE(
                (
                    SELECT content
                    FROM messages m
                    WHERE m.chat_session_id = s.id
                    ORDER BY m.id DESC
                    LIMIT 1
                ),
                ''
            ) AS last_message
        FROM chat_sessions s
        WHERE s.id = ?
        """,
        (session_id,),
    ).fetchone()
    messages = get_session_messages(db, session_id)
    return jsonify(
        {
            "session": serialize_chat_session(enriched_session),
            "messages": [serialize_message(message) for message in messages],
        }
    )


@app.route("/api/chats/<int:session_id>/messages", methods=["POST"])
@api_login_required
def send_message(session_id: int):
    user = current_user()
    db = get_db()
    chat_session = get_session_for_user(db, session_id, user["id"])
    if not chat_session:
        return json_error("Chat session not found.", 404)

    if has_pending_assistant_message(db, session_id):
        return json_error("Please wait for the current response to finish.", 409)

    payload = request.get_json(silent=True) or {}
    user_message = str(payload.get("content", "")).strip()
    if not user_message:
        return json_error("Please enter a message before sending.", 400)

    therapist = OllamaTherapist(chat_session["model_name"])
    emotional_state = therapist.detect_emotional_state(user_message)

    user_row = create_message(db, session_id, "user", user_message, emotional_state=emotional_state)
    maybe_update_chat_title(db, session_id, user_message)
    assistant_row = create_message(db, session_id, "assistant", "", status="pending")

    worker = threading.Thread(
        target=generate_assistant_reply,
        args=(session_id, assistant_row["id"], emotional_state),
        daemon=True,
    )
    worker.start()

    return jsonify(
        {
            "userMessage": serialize_message(user_row),
            "assistantMessage": serialize_message(assistant_row),
        }
    ), 202


init_db()


if __name__ == "__main__":
    host = os.getenv("THERAPY_HOST", "0.0.0.0")
    port = int(os.getenv("THERAPY_PORT", "8005"))
    app.run(host=host, port=port, debug=False, threaded=True)
