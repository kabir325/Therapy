import ChatShell from "../../../components/chat-shell";

export default async function ChatPage({ params }) {
  const { sessionId } = await params;
  return <ChatShell sessionId={sessionId} />;
}
