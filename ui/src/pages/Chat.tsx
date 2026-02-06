import { useEffect, useMemo, useState } from "react";
import GlassCard from "../components/GlassCard";
import { apiPost } from "../lib/api";

type EventMessage = {
  type: string;
  payload: Record<string, any>;
  timestamp?: string;
};

export default function Chat() {
  const [events, setEvents] = useState([] as EventMessage[]);
  const [runId, setRunId] = useState(1);
  const [message, setMessage] = useState("");
  const [connected, setConnected] = useState(false);
  const [typing, setTyping] = useState(false);
  const [attachment, setAttachment] = useState(null as File | null);

  useEffect(() => {
    const socket = new WebSocket(`ws://${window.location.host}/ws/events`);
    socket.onopen = () => setConnected(true);
    socket.onclose = () => setConnected(false);
    socket.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        setEvents((prev: EventMessage[]) => [...prev.slice(-200), payload]);
      } catch {
        // ignore
      }
    };
    return () => socket.close();
  }, []);

  const chatMessages = useMemo(
    () =>
      events
        .filter((event: EventMessage) => event.type === "chat.message")
        .map((event: EventMessage) => ({
          agent: String(event.payload.agent ?? "agent"),
          role: String(event.payload.role ?? "role"),
          content: String(event.payload.content ?? "")
        })),
    [events]
  );

  const sendMessage = async () => {
    if (!message.trim()) {
      return;
    }
    await apiPost("/chat/send", { run_id: runId, message });
    setMessage("");
  };

  const introTeam = async () => {
    await apiPost("/chat/intro", { run_id: runId });
  };
  const uploadAttachment = async () => {
    if (!attachment) {
      return;
    }
    const form = new FormData();
    form.append("file", attachment);
    await fetch(`/chat/upload?run_id=${runId}`, {
      method: "POST",
      body: form
    });
    setAttachment(null);
  };

  return (
    <section>
      <div className="page-header">
        <div>
          <div className="page-title">Chat</div>
          <div className="page-subtitle">Stakeholder + Agent conversation</div>
        </div>
        <span className="pill">{connected ? "connected" : "offline"}</span>
      </div>
      <div className="card" style={{ minHeight: 420 }}>
        <div style={{ maxHeight: 420, overflowY: "auto" }}>
          {chatMessages.length === 0 && <div className="muted">No messages yet.</div>}
          {chatMessages.map(
            (msg: { agent: string; role: string; content: string }, index: number) => (
              <div
                key={index}
                style={{
                  marginBottom: 12,
                  display: "flex",
                  justifyContent: msg.role === "Stakeholder" ? "flex-end" : "flex-start"
                }}
              >
                <div
                  style={{
                    maxWidth: "70%",
                    padding: "10px 12px",
                    borderRadius: 14,
                    background:
                      msg.role === "Stakeholder"
                        ? "linear-gradient(135deg, #7aa2ff, #57d9a3)"
                        : "rgba(20,26,40,0.8)",
                    color: msg.role === "Stakeholder" ? "#0b0f19" : "var(--text)"
                  }}
                >
                  <div style={{ fontSize: 12, opacity: 0.7 }}>{msg.agent}</div>
                  <div>{msg.content}</div>
                </div>
              </div>
            )
          )}
          {typing && <div className="muted">Agent is typing…</div>}
        </div>
      </div>
      <div className="card">
        <div className="row">
          <input
            type="number"
            value={runId}
            onChange={(e) => setRunId(Number(e.target.value))}
          />
          <input
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="Type feedback. Use @Name to target an agent."
          />
          <button onClick={sendMessage}>Send</button>
          <button onClick={introTeam} className="secondary">
            Introduce Team
          </button>
          <input
            type="file"
            onChange={(e) => setAttachment(e.target.files?.[0] ?? null)}
          />
          <button onClick={uploadAttachment} className="secondary">
            Attach
          </button>
          <button onClick={() => setTyping(!typing)} className="secondary">
            Toggle Typing
          </button>
        </div>
      </div>
    </section>
  );
}
