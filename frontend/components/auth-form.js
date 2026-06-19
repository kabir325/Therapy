"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { apiFetch } from "../lib/api";

const formConfig = {
  login: {
    title: "Welcome back",
    subtitle: "Pick up your saved sessions from any phone or laptop on your network.",
    submitLabel: "Log in",
    alternateText: "Need an account?",
    alternateHref: "/signup",
    alternateLabel: "Sign up"
  },
  signup: {
    title: "Create your account",
    subtitle: "Each user gets private sessions, saved history, and browser access after login.",
    submitLabel: "Create account",
    alternateText: "Already have an account?",
    alternateHref: "/login",
    alternateLabel: "Log in"
  }
};

export default function AuthForm({ mode }) {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const config = formConfig[mode];

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setIsSubmitting(true);

    try {
      if (mode === "signup") {
        await apiFetch("/api/auth/signup", {
          method: "POST",
          body: JSON.stringify({
            username,
            password,
            confirmPassword
          })
        });
      } else {
        await apiFetch("/api/auth/login", {
          method: "POST",
          body: JSON.stringify({
            username,
            password
          })
        });
      }

      router.replace("/");
    } catch (err) {
      setError(err.message);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="center-screen">
      <section className="auth-shell">
        <div className="auth-hero">
          <span className="eyebrow">Therepy</span>
          <h1>{config.title}</h1>
          <p>{config.subtitle}</p>
          <div className="hero-card">
            <span>Mobile first</span>
            <span>Saved sessions</span>
            <span>Private local AI</span>
          </div>
        </div>

        <form className="panel auth-form" onSubmit={handleSubmit}>
          <label>
            Username
            <input
              autoComplete="username"
              onChange={(event) => setUsername(event.target.value)}
              placeholder="Enter your username"
              required
              type="text"
              value={username}
            />
          </label>

          <label>
            Password
            <input
              autoComplete={mode === "signup" ? "new-password" : "current-password"}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="At least 8 characters"
              required
              type="password"
              value={password}
            />
          </label>

          {mode === "signup" ? (
            <label>
              Confirm password
              <input
                autoComplete="new-password"
                onChange={(event) => setConfirmPassword(event.target.value)}
                placeholder="Repeat your password"
                required
                type="password"
                value={confirmPassword}
              />
            </label>
          ) : null}

          {error ? <p className="form-error">{error}</p> : null}

          <button className="primary-button" disabled={isSubmitting} type="submit">
            {isSubmitting ? "Please wait..." : config.submitLabel}
          </button>

          <p className="muted-row">
            {config.alternateText} <Link href={config.alternateHref}>{config.alternateLabel}</Link>
          </p>
        </form>
      </section>
    </main>
  );
}
