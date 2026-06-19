# Therepy

Therepy now uses:

- A Flask backend API for auth, chat storage, and Ollama access
- A Next.js frontend for a cleaner mobile-first browser experience
- Async message handling so sending feels instant even when the Raspberry Pi is still generating the reply

## What changed

- Messages no longer wait for the full Ollama response before returning to the browser
- The UI is now built for phone and laptop screens
- Chat sessions remain saved per user after login
- The frontend shows an animated thinking state while the model is generating
- The backend keeps recent session context for each reply

## Why it felt slow before

The previous Flask page submitted one blocking request that only returned after Ollama finished generating. On a Raspberry Pi that can easily feel like the message itself is stuck.

Now the flow is:

1. Save the user message immediately
2. Create a pending assistant message
3. Generate the reply in a background thread
4. Poll from the frontend and replace the pending bubble when the response is ready

That makes the app feel much faster and fixes the "message taking forever to send" problem.

## Recommended model

Default model: `qwen2.5:1.5b`

Why this is the new default:

- Better Raspberry Pi speed than 3B models
- Better quality than the very tiny fallback models
- Good balance for mobile browser use where responsiveness matters

If your Pi has more RAM and you want higher quality, try:

```bash
export THERAPY_MODEL=qwen2.5:3b
```

## Project structure

- `app.py`: Flask backend API
- `start_therapy.py`: backend launcher
- `frontend/`: Next.js frontend
- `therepy.db`: SQLite database for users, sessions, and messages

## Backend setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export THERAPY_SECRET_KEY='replace-this-with-a-long-random-secret'
export THERAPY_MODEL=qwen2.5:1.5b
ollama pull qwen2.5:1.5b
python start_therapy.py
```

Backend default URL:

```text
http://YOUR_PI_IP:8000
```

## Frontend setup

Copy the example env file and point it at the backend:

```bash
cd frontend
cp .env.local.example .env.local
```

Set:

```text
NEXT_PUBLIC_API_BASE_URL=http://YOUR_PI_IP:8000
```

Then install and run:

```bash
npm install
npm run dev
```

Frontend default URL:

```text
http://YOUR_PI_IP:3000
```

## Raspberry Pi network setup

If your frontend runs on port `3000`, the backend must allow that browser origin.

Example:

```bash
export THERAPY_ALLOWED_ORIGINS=http://YOUR_PI_IP:3000
```

If you also want local desktop development, you can use multiple origins:

```bash
export THERAPY_ALLOWED_ORIGINS=http://YOUR_PI_IP:3000,http://localhost:3000,http://127.0.0.1:3000
```

## Production-style deployment on the Pi

A clean setup is:

1. Run the Flask backend on port `8000`
2. Run the Next.js frontend on port `3000`
3. Put Nginx in front if you want one clean domain or IP entry point
4. Use `systemd` to auto-start both services on boot

## Data storage

- Users, sessions, and messages are stored in `therepy.db`
- Passwords are stored hashed
- Login state uses secure Flask session cookies
- Message status can be `pending`, `complete`, or `error`

## Notes on responsiveness

- The backend now only sends the most recent session messages to the model to reduce prompt size
- `qwen2.5:1.5b` is chosen to reduce Raspberry Pi response time
- The frontend disables duplicate sends while one reply is still pending

## Important safety note

This is a supportive chat tool, not a replacement for licensed mental health care, diagnosis, or emergency services.
