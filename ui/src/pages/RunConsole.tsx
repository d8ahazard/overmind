import { useEffect, useMemo, useState } from "react";
import AgentChat from "../components/AgentChat";
import { BarChart, StatRow } from "../components/Charts";
import FileDiff from "../components/FileDiff";
import MermaidPanel from "../components/MermaidPanel";
import TeamChat from "../components/TeamChat";
import TaskTimeline from "../components/TaskTimeline";
import Workflow from "../components/Workflow";
import BoardSummary from "../components/BoardSummary";
import { apiGet, apiPost } from "../lib/api";

type EventMessage = {
  type: string;
  payload: Record<string, any>;
  timestamp?: string;
};

export default function RunConsole() {
  const [events, setEvents] = useState([] as EventMessage[]);
  const [runId, setRunId] = useState(1);
  const [connected, setConnected] = useState(false);
  const [seedInfo, setSeedInfo] = useState(null as string | null);
  const [historyLoaded, setHistoryLoaded] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(null as number | null);
  const [selectedEvent, setSelectedEvent] = useState(null as EventMessage | null);
  const [metricsProject, setMetricsProject] = useState(null as Record<string, any> | null);
  const [metricsGlobal, setMetricsGlobal] = useState(null as Record<string, any> | null);
  const [metricsScope, setMetricsScope] = useState("project");
  const [goals, setGoals] = useState([] as { id: number; title: string; status: string }[]);

  useEffect(() => {
    const socket = new WebSocket(`ws://${window.location.host}/ws/events`);
    socket.onopen = () => setConnected(true);
    socket.onclose = () => setConnected(false);
    socket.onmessage = (message) => {
      try {
        const payload = JSON.parse(message.data);
        setEvents((prev: EventMessage[]) => [...prev.slice(-200), payload as EventMessage]);
      } catch {
        // ignore malformed messages
      }
    };
    return () => socket.close();
  }, []);

  useEffect(() => {
    const loadHistory = async () => {
      try {
        const history = (await apiGet(
          runId ? `/events/history?run_id=${runId}` : "/events/history"
        )) as { run_id: number | null; events: EventMessage[] };
        if (history.run_id && !runId) {
          setRunId(history.run_id);
        }
        if (history.events.length) {
          setEvents((prev: EventMessage[]) => [...history.events, ...prev].slice(-400));
        }
      } catch {
        // ignore history load errors
      } finally {
        setHistoryLoaded(true);
      }
    };
    void loadHistory();
  }, [runId]);

  useEffect(() => {
    const loadMetrics = async () => {
      try {
        const project = (await apiGet("/metrics/summary?scope=project")) as Record<string, any>;
        const global = (await apiGet("/metrics/summary?scope=global")) as Record<string, any>;
        setMetricsProject(project);
        setMetricsGlobal(global);
        const goalData = (await apiGet("/goals")) as {
          id: number;
          title: string;
          status: string;
        }[];
        setGoals(goalData);
      } catch {
        // ignore metrics errors
      }
    };
    void loadMetrics();
  }, [runId]);

  const agentMessages = useMemo(
    () =>
      events
        .filter((event: EventMessage) => event.type === "agent.response")
        .map((event: EventMessage) => ({
          role: String(event.payload.agent ?? "agent"),
          content: String(event.payload.content ?? ""),
          timestamp: event.timestamp
        })),
    [events]
  );

  const fileEvents = useMemo(
    () =>
      events
        .filter((event: EventMessage) => event.type?.startsWith("file."))
        .map((event: EventMessage) => ({
          type: event.type,
          path: String(event.payload.path ?? "")
        })),
    [events]
  );

  const chatMessages = useMemo(
    () =>
      events
        .filter((event: EventMessage) => event.type === "chat.message")
        .map((event: EventMessage) => ({
          agent: String(event.payload.agent ?? "agent"),
          role: String(event.payload.role ?? "role"),
          content: String(event.payload.content ?? ""),
          timestamp: event.timestamp
        })),
    [events]
  );

  const memoryNotes = useMemo(
    () =>
      events
        .filter((event: EventMessage) => event.type === "memory.updated")
        .map((event: EventMessage) => ({
          agent: String(event.payload.agent ?? "agent"),
          content: String(event.payload.content ?? "")
        })),
    [events]
  );

  const stats = useMemo(
    () => [
      { label: "Events", value: String(events.length) },
      {
        label: "Agents",
        value: String(new Set(agentMessages.map((m: { role: string }) => m.role)).size)
      },
      { label: "Files", value: String(fileEvents.length) },
      { label: "Memory Updates", value: String(memoryNotes.length) }
    ],
    [events.length, agentMessages, fileEvents.length, memoryNotes.length]
  );

  const workflowSteps = [
    { label: "Intake", status: "done" as const },
    { label: "Planning", status: "done" as const },
    { label: "Execution", status: "active" as const },
    { label: "Testing", status: "pending" as const },
    { label: "Review", status: "pending" as const },
    { label: "Release", status: "pending" as const }
  ];

  const startRun = async () => {
    await apiPost(`/runs/${runId}/start`, {});
  };

  const seedDefault = async () => {
    const result = await apiPost<{ run_id: number }>("/seed", {});
    setRunId(result.run_id);
    setSeedInfo(`Seeded run ${result.run_id}`);
  };

  const activeMetrics = metricsScope === "global" ? metricsGlobal : metricsProject;
  const toolBreakdown = activeMetrics?.tool_breakdown || {};
  const toolPoints = Object.entries(toolBreakdown).map(([label, value]) => ({
    label,
    value: Number(value)
  }));

  return (
    <section>
      <div className="page-header">
        <div>
          <div className="page-title">Run Console</div>
          <div className="page-subtitle">Executive dashboard for live runs</div>
        </div>
      </div>
      <div className="card">
        <div className="row">
          <span className="pill">Status: {connected ? "connected" : "disconnected"}</span>
          <input
            type="number"
            value={runId}
            onChange={(e) => setRunId(Number(e.target.value))}
          />
          <button onClick={seedDefault}>Seed Default</button>
          <button onClick={startRun} className="secondary">
            Start Run
          </button>
          {seedInfo && <span className="pill">{seedInfo}</span>}
        </div>
        <div className="row" style={{ marginTop: 8 }}>
          <button
            className={metricsScope === "project" ? "secondary" : ""}
            onClick={() => setMetricsScope("project")}
          >
            Project View
          </button>
          <button
            className={metricsScope === "global" ? "secondary" : ""}
            onClick={() => setMetricsScope("global")}
          >
            Global View
          </button>
        </div>
      </div>
      <div className="grid-3">
        <StatRow
          title="Run Stats"
          stats={[
            ...stats,
            { label: "Tool Calls", value: String(activeMetrics?.tool_calls ?? 0) },
            { label: "Errors", value: String(activeMetrics?.tool_errors ?? 0) }
          ]}
        />
        <div className="card glow">
          <h3>Executive Summary</h3>
          <p className="muted">
            Run is active. MCP tools available. Stakeholder feedback routed to managers by
            default. Latest memory updates are tracked below.
          </p>
          <div className="row">
            <span className="pill">
              Budget: ${activeMetrics?.budget?.usd_spent ?? 0} / $
              {activeMetrics?.budget?.usd_limit ?? 0}
            </span>
            <span className="pill">
              Approvals: {activeMetrics?.approvals_pending ?? 0} pending
            </span>
            <span className="pill">Goals: {Object.keys(activeMetrics?.goals || {}).length}</span>
          </div>
        </div>
        <Workflow steps={workflowSteps} />
      </div>
      <div className="grid-2">
        <MermaidPanel />
        <BarChart
          title="Events by Type"
          points={[
            { label: "Chat", value: chatMessages.length },
            { label: "Memory", value: memoryNotes.length },
            { label: "Files", value: fileEvents.length },
            { label: "Agents", value: agentMessages.length }
          ]}
        />
      </div>
      <div className="grid-2">
        <BarChart title="Tool Calls" points={toolPoints} />
        <div className="card">
          <h3>Goals</h3>
          {goals.length === 0 && <div className="muted">No goals defined.</div>}
          <ul>
          {goals.map((goal: { id: number; title: string; status: string }) => (
              <li key={goal.id}>
                {goal.title} <span className="pill">{goal.status}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
      <div className="grid-2">
        <TaskTimeline
          events={events}
          selectedIndex={selectedIndex}
          onSelect={(index, event) => {
            setSelectedIndex(index);
            setSelectedEvent(event);
          }}
        />
        <div className="card">
          <h3>Event Details</h3>
          {selectedEvent ? (
            <pre style={{ whiteSpace: "pre-wrap" }}>
              {JSON.stringify(selectedEvent, null, 2)}
            </pre>
          ) : (
            <div className="muted">Click a timeline event to view details.</div>
          )}
        </div>
        <div className="card">
          <h3>Stakeholder Signals</h3>
          <div className="muted">
            Manager feedback required when stakeholder messages arrive without @mentions.
          </div>
          <div className="row">
            <span className="pill">Requests: {chatMessages.length}</span>
            <span className="pill">Pending: 0</span>
          </div>
        </div>
      </div>
      <div className="grid-2">
        <BoardSummary />
        <div className="card">
          <h3>Goals Met</h3>
          <div className="row">
            <span className="pill">Met: 4</span>
            <span className="pill">Pending: 3</span>
            <span className="pill">At Risk: 1</span>
          </div>
          <div className="muted" style={{ marginTop: 8 }}>
            Executive goal tracking is summarized from task states and test reports.
          </div>
        </div>
      </div>
      <div className="grid-2">
        <TeamChat messages={chatMessages} />
        <AgentChat messages={agentMessages} />
      </div>
      <div className="grid-2">
        <FileDiff files={fileEvents} />
        <div className="card">
          <h3>Memory Feed</h3>
          {memoryNotes.length === 0 && <p>No memory updates yet.</p>}
          {memoryNotes.map((note: { agent: string; content: string }, index: number) => (
            <div key={index} style={{ marginBottom: 8 }}>
              <strong>{note.agent}:</strong> {note.content}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
