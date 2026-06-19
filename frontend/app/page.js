"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import LoadingScreen from "../components/loading-screen";
import { apiFetch } from "../lib/api";

export default function HomePage() {
  const router = useRouter();

  useEffect(() => {
    async function bootstrap() {
      try {
        const authPayload = await apiFetch("/api/auth/me");
        if (!authPayload.user) {
          router.replace("/login");
          return;
        }

        const chatsPayload = await apiFetch("/api/chats");
        if (chatsPayload.sessions.length > 0) {
          router.replace(`/chat/${chatsPayload.sessions[0].id}`);
          return;
        }

        const newChatPayload = await apiFetch("/api/chats", {
          method: "POST"
        });
        router.replace(`/chat/${newChatPayload.session.id}`);
      } catch {
        router.replace("/login");
      }
    }

    bootstrap();
  }, [router]);

  return <LoadingScreen title="Setting up Therepy..." />;
}
