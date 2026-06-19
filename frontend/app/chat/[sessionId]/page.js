import ChatShell from "../../../components/chat-shell";

export default function ChatPage({ params }) {
  return <ChatShell sessionId={params.sessionId} />;
}
