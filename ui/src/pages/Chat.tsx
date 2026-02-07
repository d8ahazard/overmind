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
  const [pendingAgents, setPendingAgents] = useState([] as string[]);
  const [attachment, setAttachment] = useState(null as File | null);
  const [error, setError] = useState(null as string | null);
  const [activity, setActivity] = useState([] as string[]);
  const [thinkingAgents, setThinkingAgents] = useState([] as string[]);
  const [pauseMode, setPauseMode] = useState(null as string | null);
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
        if (payload?.type === "chat.message") {
          const agent = String(payload?.payload?.agent ?? "");
          if (agent && agent !== "Stakeholder") {
            setPendingAgents((prev: string[]) => prev.filter((name: string) => name !== agent));
          }
        }
        if (payload?.type === "tool.requested") {
          const tool = payload?.payload?.tool ?? "tool";
          const actor = payload?.payload?.actor ?? "agent";
          const args = payload?.payload?.arguments ?? {};
          const command = args.command ? ` ${args.command}` : "";
          const name = args.name ? ` ${args.name}` : "";
          const url = args.url ? ` ${args.url}` : "";
          const line = `[${actor}] ${tool}${command}${name}${url}`;
          setActivity((prev: string[]) => [...prev.slice(-9), line]);
          console.log("tool.requested", payload.payload);
        }
        if (payload?.type === "agent.thinking") {
          const actor = payload?.payload?.agent ?? "agent";
          const reason = payload?.payload?.reason ?? "thinking";
          const line = `[${actor}] ${reason}`;
          setActivity((prev: string[]) => [...prev.slice(-9), line]);
        }
        if (payload?.type === "agent.thinking") {
          const actor = String(payload?.payload?.agent ?? "");
          if (actor) {
            setThinkingAgents((prev: string[]) =>
              prev.includes(actor) ? prev : [...prev, actor]
            );
          }
        }
        if (payload?.type === "agent.thinking.done") {
          const actor = String(payload?.payload?.agent ?? "");
          if (actor) {
            setThinkingAgents((prev: string[]) => prev.filter((name) => name !== actor));
          }
        }
        if (payload?.type === "tool.completed") {
          console.log("tool.completed", payload.payload);
        }
        if (payload?.type === "team.break") {
          setPauseMode("break");
        }
        if (payload?.type === "team.attention") {
          setPauseMode("attention");
        }
        if (payload?.type === "team.resume") {
          setPauseMode(null);
        }
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
    setTyping(pendingAgents.length > 0);
  }, [pendingAgents]);

  useEffect(() => {
    const loadHistory = async () => {
      try {
        const history = (await apiGet(
          runId ? `/chat/history?run_id=${runId}` : "/chat/history"
        )) as {
          run_id: number | null;
          messages: ChatHistoryItem[];
          pause_mode?: string | null;
        };
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
        if (history.pause_mode) {
          setPauseMode(history.pause_mode);
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
          content: String(event.payload.content ?? ""),
          timestamp: event.payload.timestamp ?? event.timestamp
        })),
    [events]
  );

  const formatTime = (value?: string) => {
    if (!value) {
      return "";
    }
    const normalized = /[zZ]|[+-]\d{2}:?\d{2}$/.test(value) ? value : `${value}Z`;
    const date = new Date(normalized);
    if (Number.isNaN(date.getTime())) {
      return "";
    }
    return new Intl.DateTimeFormat(undefined, {
      hour: "numeric",
      minute: "2-digit",
      timeZoneName: "short"
    }).format(date);
  };

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
      const result = (await apiPost("/chat/send", payload)) as {
        run_id?: number;
        targets?: string[];
      };
      if (result.run_id && !runId) {
        setRunId(result.run_id);
      }
      if (result.targets?.length) {
        setPendingAgents(result.targets);
        setTyping(true);
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
          {pauseMode && (
            <div className="muted" style={{ marginBottom: 8 }}>
              {pauseMode === "break"
                ? "Break mode active. Team work is paused."
                : "Attention mode active. Team meeting requested."}
            </div>
          )}
          {chatMessages.length === 0 && <div className="muted">No messages yet.</div>}
          {chatMessages.map(
            (
              msg: { agent: string; role: string; content: string; timestamp?: string },
              index: number
            ) => (
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
                  <div style={{ fontSize: 12, opacity: 0.7 }}>
                    {msg.agent}
                    {msg.timestamp && (
                      <span style={{ marginLeft: 8 }}>{formatTime(msg.timestamp)}</span>
                    )}
                  </div>
                  <div>{msg.content}</div>
                </div>
              </div>
            )
          )}
          {typing && (
            <div className="muted">
              {pendingAgents.length
                ? `Awaiting: ${pendingAgents.join(", ")}…`
                : "Agent is typing…"}
            </div>
          )}
          {thinkingAgents.length > 0 && (
            <div className="muted">Thinking: {thinkingAgents.join(", ")}</div>
          )}
          {activity.length > 0 && (
            <div className="muted" style={{ marginTop: 8 }}>
              Activity: {activity.join(" · ")}
            </div>
          )}
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
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                event.preventDefault();
                void sendMessage();
              }
            }}
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
