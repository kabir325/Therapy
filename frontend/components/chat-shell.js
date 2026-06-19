"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { apiFetch } from "../lib/api";
import ThinkingIndicator from "./thinking-indicator";

function formatTimestamp(value) {
  if (!value) {
    return "";
  }

  const date = new Date(value);
  return date.toLocaleString([], {
    hour: "numeric",
    minute: "2-digit",
    month: "short",
    day: "numeric"
  });
}

export default function ChatShell({ sessionId }) {
  const router = useRouter();
  const [authUser, setAuthUser] = useState(null);
  const [chatSession, setChatSession] = useState(null);
  const [sessions, setSessions] = useState([]);
  const [messages, setMessages] = useState([]);
  const [draft, setDraft] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isSending, setIsSending] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);

  const hasPendingAssistant = useMemo(
    () => messages.some((message) => message.role === "assistant" && message.status === "pending"),
    [messages]
  );
  const hasValidSessionId = Boolean(sessionId) && sessionId !== "undefined";

  async function loadChat({ withLoading = false } = {}) {
    if (!hasValidSessionId) {
      setError("This chat session could not be loaded.");
      setIsLoading(false);
      return;
    }

    try {
      if (withLoading) {
        setIsLoading(true);
      }

      const [authPayload, sessionsPayload, chatPayload] = await Promise.all([
        apiFetch("/api/auth/me"),
        apiFetch("/api/chats"),
        apiFetch(`/api/chats/${sessionId}`)
      ]);

      if (!authPayload.user) {
        router.replace("/login");
        return;
      }

      setAuthUser(authPayload.user);
      setSessions(sessionsPayload.sessions);
      setChatSession(chatPayload.session);
      setMessages(chatPayload.messages);
      setError("");
    } catch (err) {
      if (err.status === 401) {
        router.replace("/login");
        return;
      }
      setError(err.message);
    } finally {
      if (withLoading) {
        setIsLoading(false);
      }
    }
  }

  useEffect(() => {
    loadChat({ withLoading: true });
  }, [sessionId]);

  useEffect(() => {
    if (!hasPendingAssistant) {
      return undefined;
    }

    const intervalId = setInterval(() => {
      loadChat();
    }, 1500);

    return () => clearInterval(intervalId);
  }, [hasPendingAssistant, sessionId]);

  async function handleNewChat() {
    try {
      const payload = await apiFetch("/api/chats", { method: "POST" });
      router.push(`/chat/${payload.session.id}`);
      setMenuOpen(false);
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleLogout() {
    try {
      await apiFetch("/api/auth/logout", { method: "POST" });
      router.replace("/login");
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleSend(event) {
    event.preventDefault();
    const content = draft.trim();
    if (!content || isSending || hasPendingAssistant || !hasValidSessionId) {
      return;
    }

    const temporaryUserMessage = {
      id: `tmp-user-${Date.now()}`,
      role: "user",
      content,
      status: "complete",
      createdAt: new Date().toISOString()
    };
    const temporaryAssistantMessage = {
      id: `tmp-assistant-${Date.now()}`,
      role: "assistant",
      content: "",
      status: "pending",
      createdAt: new Date().toISOString()
    };

    setMessages((currentMessages) => [
      ...currentMessages,
      temporaryUserMessage,
      temporaryAssistantMessage
    ]);
    setDraft("");
    setError("");
    setIsSending(true);

    try {
      await apiFetch(`/api/chats/${sessionId}/messages`, {
        method: "POST",
        body: JSON.stringify({ content })
      });
      await loadChat();
    } catch (err) {
      setError(err.message);
      await loadChat();
    } finally {
      setIsSending(false);
    }
  }

  if (isLoading) {
    return (
      <main className="center-screen">
        <div className="panel large-panel centered-panel">
          <div className="pulse-orb" />
          <h1>Opening your session...</h1>
          <p>Loading messages and preparing Dr. Sarah.</p>
        </div>
      </main>
    );
  }

  return (
    <main className="chat-page">
      <aside className={`sidebar ${menuOpen ? "open" : ""}`}>
        <div className="sidebar-header">
          <div>
            <span className="eyebrow">Therepy</span>
            <h2>{authUser?.username}</h2>
          </div>
          <button className="ghost-button mobile-only" onClick={() => setMenuOpen(false)} type="button">
            Close
          </button>
        </div>

        <button className="primary-button" onClick={handleNewChat} type="button">
          New chat
        </button>

        <nav className="session-list">
          {sessions.map((session) => (
            <Link
              className={`session-link ${String(session.id) === String(sessionId) ? "active" : ""}`}
              href={`/chat/${session.id}`}
              key={session.id}
              onClick={() => setMenuOpen(false)}
            >
              <span className="session-link-title">{session.title}</span>
              <span className="session-link-meta">{formatTimestamp(session.updatedAt)}</span>
              <span className="session-link-preview">{session.lastMessage || "No messages yet"}</span>
            </Link>
          ))}
        </nav>

        <div className="sidebar-footer">
          <button className="secondary-button" onClick={handleLogout} type="button">
            Log out
          </button>
        </div>
      </aside>

      {menuOpen ? <div className="sidebar-backdrop" onClick={() => setMenuOpen(false)} /> : null}

      <section className="chat-shell">
        <header className="chat-header">
          <div className="chat-header-main">
            <button className="ghost-button mobile-only" onClick={() => setMenuOpen(true)} type="button">
              Menu
            </button>
            <div>
              <span className="eyebrow">Session</span>
              <h1>{chatSession?.title || "New chat"}</h1>
              <p>Fast local chat on your Raspberry Pi with saved context and phone-friendly UI.</p>
            </div>
          </div>

          <div className="status-pill">
            <span>Model</span>
            <strong>{chatSession?.modelName}</strong>
          </div>
        </header>

        {error ? <div className="banner-error">{error}</div> : null}

        <section className="messages-panel">
          {messages.length === 0 ? (
            <div className="empty-chat">
              <div className="empty-chat-icon">S</div>
              <h2>Start talking whenever you are ready</h2>
              <p>Your message sends immediately, and Dr. Sarah will respond as soon as the Pi finishes processing.</p>
            </div>
          ) : (
            messages.map((message) => (
              <article className={`message-card ${message.role}`} key={message.id}>
                <div className="message-topline">
                  <span>{message.role === "user" ? "You" : "Dr. Sarah"}</span>
                  <span>{formatTimestamp(message.updatedAt || message.createdAt)}</span>
                </div>

                {message.role === "assistant" && message.status === "pending" ? (
                  <div className="message-thinking">
                    <ThinkingIndicator />
                    <p>Dr. Sarah is thinking...</p>
                  </div>
                ) : (
                  <p className="message-content">{message.content}</p>
                )}

                {message.status === "error" ? (
                  <p className="message-error">The response failed. You can try sending another message.</p>
                ) : null}
              </article>
            ))
          )}
        </section>

        <form className="composer" onSubmit={handleSend}>
          <textarea
            disabled={hasPendingAssistant || isSending}
            onChange={(event) => setDraft(event.target.value)}
            placeholder={hasPendingAssistant ? "Waiting for the current response..." : "Type what is on your mind..."}
            rows={4}
            value={draft}
          />

          <div className="composer-row">
            <p className="composer-hint">
              For urgent safety concerns, contact local emergency support or a licensed professional immediately.
            </p>

            <button
              className="primary-button composer-button"
              disabled={!draft.trim() || isSending || hasPendingAssistant}
              type="submit"
            >
              {hasPendingAssistant ? "Thinking..." : isSending ? "Sending..." : "Send"}
            </button>
          </div>
        </form>
      </section>
    </main>
  );
}
