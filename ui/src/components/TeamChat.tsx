type ChatMessage = {
  agent: string;
  role: string;
  content: string;
  timestamp?: string;
};

export default function TeamChat({ messages }: { messages: ChatMessage[] }) {
  return (
    <section>
      <h3>Team Chat</h3>
      <div style={{ border: "1px solid #eee", padding: 8, minHeight: 160 }}>
        {messages.length === 0 && <p>No chat messages yet.</p>}
        {messages.map((message, index) => (
          <div key={index} style={{ marginBottom: 8 }}>
            <strong>{message.agent}</strong>{" "}
            <span style={{ color: "#888", fontSize: 12 }}>({message.role})</span>
            <div>{message.content}</div>
          </div>
        ))}
      </div>
    </section>
  );
}
