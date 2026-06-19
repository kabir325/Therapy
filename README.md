# Therepy Web App

This project now runs as a browser-based multi-user therapy chat app backed by Ollama.

## What it does

- Signup and login from the browser
- Separate saved chat sessions for each user
- Chat history that stays available after login
- Persistent conversation context for each session
- Ollama-powered therapist responses using a Raspberry Pi friendly model

## Recommended model

Default model: `llama3.2:3b`

Why this default:

- Stronger than tiny models like TinyLlama
- Small enough to be realistic on a Raspberry Pi compared with 7B+ models
- Good balance of quality, memory use, and speed for local hosting

You can change the model with:

```bash
export THERAPY_MODEL=qwen2.5:3b
```

`qwen2.5:3b` is another good option if you want to compare quality and speed.

## Local setup

1. Create a virtual environment.
2. Install Python dependencies.
3. Install and start Ollama.
4. Pull the model.
5. Start the app.

Example:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
ollama pull llama3.2:3b
python start_therapy.py
```

The app listens on `0.0.0.0:8000` by default, so other devices on the same network can reach it.

## Raspberry Pi deployment

Use Raspberry Pi OS 64-bit if possible. Larger RAM helps a lot for model performance.

1. Install Python 3 and `pip`.
2. Install Ollama on the Pi.
3. Clone or copy this project to the Pi.
4. Install requirements:

```bash
pip install -r requirements.txt
```

5. Pull the default model:

```bash
ollama pull llama3.2:3b
```

6. Set a strong secret key before deployment:

```bash
export THERAPY_SECRET_KEY='replace-this-with-a-long-random-secret'
```

7. Start the app:

```bash
python start_therapy.py
```

8. Open it from another device:

```text
http://YOUR_PI_IP:8000
```

## Optional production notes

- Put Nginx in front of the app if you want a cleaner local-network deployment.
- Run the app with `systemd` on the Pi so it starts automatically on boot.
- Back up `therepy.db` because it contains users, sessions, and messages.

## Data storage

- Users, chat sessions, and messages are stored in `therepy.db`
- Browser login state uses Flask sessions
- Conversation context is rebuilt from saved messages in each chat session

## Important safety note

This is a supportive chat tool, not a replacement for licensed mental health care, diagnosis, or emergency services.
