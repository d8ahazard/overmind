import { useEffect, useMemo, useRef, useState } from "react";
import { apiGet, apiPost } from "../lib/api";

type EventMessage = {
  type: string;
  payload: Record<string, any>;
  timestamp?: string;
};

type ChatHistoryItem = {
  role?: string;
  agent?: string;
  content?: string;
  timestamp?: string;
  message_id?: string;
};

export default function Chat() {
  const [events, setEvents] = useState([] as EventMessage[]);
  const [runId, setRunId] = useState(0);
  const [message, setMessage] = useState("");
  const [connected, setConnected] = useState(false);
  const [typing, setTyping] = useState(false);
  const [attachment, setAttachment] = useState(null as File | null);
  const [error, setError] = useState(null as string | null);
  const fileInputRef = useRef(null as HTMLInputElement | null);
  const seenMessageIdsRef = useRef(new Set<string>());

  useEffect(() => {
    const socket = new WebSocket(`ws://${window.location.host}/ws/events`);
    socket.onopen = () => setConnected(true);
    socket.onclose = () => setConnected(false);
    socket.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        const msgId = payload?.payload?.message_id;
        if (msgId && seenMessageIdsRef.current.has(msgId)) {
          return;
        }
        if (msgId) {
          seenMessageIdsRef.current.add(msgId);
        }
        setEvents((prev: EventMessage[]) => [...prev.slice(-200), payload]);
      } catch {
        // ignore
      }
    };
    return () => socket.close();
  }, []);

  useEffect(() => {
    const loadRuns = async () => {
      try {
        const runs = (await apiGet("/runs")) as { id: number }[];
        if (runs.length) {
          const latest = runs.reduce((max, item) => (item.id > max ? item.id : max), 0);
          setRunId(latest);
        }
      } catch (err) {
        setError((err as Error).message);
      }
    };
    void loadRuns();
  }, []);

  useEffect(() => {
    const loadHistory = async () => {
      try {
        const history = (await apiGet(
          runId ? `/chat/history?run_id=${runId}` : "/chat/history"
        )) as { run_id: number | null; messages: ChatHistoryItem[] };
        if (history.run_id && !runId) {
          setRunId(history.run_id);
        }
        const items = history.messages
          .filter((msg) => {
            const msgId = msg.message_id;
            if (!msgId) {
              return true;
            }
            if (seenMessageIdsRef.current.has(msgId)) {
              return false;
            }
            seenMessageIdsRef.current.add(msgId);
            return true;
          })
          .map((msg) => ({
          type: "chat.message",
          payload: {
            agent: msg.agent ?? "agent",
            role: msg.role ?? "role",
            content: msg.content ?? "",
            message_id: msg.message_id
          },
          timestamp: msg.timestamp
        }));
        if (items.length) {
          setEvents((prev: EventMessage[]) => [...items, ...prev].slice(-200));
        }
      } catch {
        // ignore history load errors
      }
    };
    void loadHistory();
  }, [runId]);

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
    setError(null);
    if (!message.trim()) {
      return;
    }
    const payload: Record<string, unknown> = { message };
    if (runId) {
      payload.run_id = runId;
    }
    try {
      const result = (await apiPost("/chat/send", payload)) as { run_id?: number };
      if (result.run_id && !runId) {
        setRunId(result.run_id);
      }
      setMessage("");
    } catch (err) {
      setError((err as Error).message);
    }
  };

  const introTeam = async () => {
    setError(null);
    const payload: Record<string, unknown> = {};
    if (runId) {
      payload.run_id = runId;
    }
    try {
      const result = (await apiPost("/chat/intro", payload)) as { run_id?: number };
      if (result.run_id && !runId) {
        setRunId(result.run_id);
      }
    } catch (err) {
      setError((err as Error).message);
    }
  };
  const uploadAttachment = async () => {
    setError(null);
    if (!attachment) {
      return;
    }
    if (!runId) {
      setError("Create or select a run before uploading attachments.");
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

  const openFilePicker = () => {
    fileInputRef.current?.click();
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
      {error && <p style={{ color: "var(--danger)" }}>{error}</p>}
      <div className="card" style={{ minHeight: 420 }}>
        <div style={{ maxHeight: 420, overflowY: "auto", paddingBottom: 8 }}>
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
        <div className="row" style={{ alignItems: "center" }}>
          <input
            type="number"
            value={runId}
            onChange={(e) => setRunId(Number(e.target.value))}
            placeholder="Run id"
            style={{ maxWidth: 140 }}
          />
          <button onClick={introTeam} className="secondary">
            Introduce Team
          </button>
          <button onClick={() => setTyping(!typing)} className="secondary">
            Toggle Typing
          </button>
        </div>
        <div className="row" style={{ marginTop: 8, alignItems: "center" }}>
          <button onClick={openFilePicker} className="secondary">
            +
          </button>
          <input
            ref={fileInputRef}
            type="file"
            style={{ display: "none" }}
            onChange={(e) => setAttachment(e.target.files?.[0] ?? null)}
          />
          <input
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="Type a message. Use @Name to target an agent."
            style={{ flex: 1 }}
          />
          <button onClick={uploadAttachment} className="secondary" disabled={!attachment}>
            Attach
          </button>
          <button onClick={sendMessage}>Send</button>
        </div>
      </div>
    </section>
  );
}
