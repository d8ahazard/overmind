type TimelineEvent = {
  type: string;
  payload: Record<string, unknown>;
  timestamp?: string;
};

export default function TaskTimeline({ events }: { events: TimelineEvent[] }) {
  return (
    <section>
      <h3>Timeline</h3>
      <div style={{ border: "1px solid #eee", padding: 8, minHeight: 120 }}>
        {events.length === 0 && <p>No events yet.</p>}
        {events.map((event, index) => (
          <div key={index} style={{ marginBottom: 6 }}>
            <strong>{event.type}</strong>
            <div style={{ fontSize: 12, color: "#666" }}>
              {event.timestamp ?? "now"}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
