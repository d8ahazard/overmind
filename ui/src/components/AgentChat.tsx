type AgentMessage = {
  role: string;
  content: string;
  timestamp?: string;
};

export default function AgentChat({ messages }: { messages: AgentMessage[] }) {
  return (
    <section>
      <h3>Agent Chat</h3>
      <div style={{ border: "1px solid #eee", padding: 8, minHeight: 120 }}>
        {messages.length === 0 && <p>No agent messages yet.</p>}
        {messages.map((message, index) => (
          <div key={index} style={{ marginBottom: 8 }}>
            <strong>{message.role}:</strong> {message.content}
          </div>
        ))}
      </div>
    </section>
  );
}
