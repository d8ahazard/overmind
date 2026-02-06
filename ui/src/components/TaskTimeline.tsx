type TimelineEvent = {
  type: string;
  payload: Record<string, unknown>;
  timestamp?: string;
};

export default function TaskTimeline({
  events,
  selectedIndex,
  onSelect
}: {
  events: TimelineEvent[];
  selectedIndex?: number | null;
  onSelect?: (index: number, event: TimelineEvent) => void;
}) {
  return (
    <section>
      <h3>Timeline</h3>
      <div style={{ border: "1px solid #eee", padding: 8, minHeight: 120 }}>
        {events.length === 0 && <p>No events yet.</p>}
        {events.map((event, index) => (
          <div
            key={index}
            onClick={() => onSelect && onSelect(index, event)}
            style={{
              marginBottom: 6,
              cursor: onSelect ? "pointer" : "default",
              padding: "6px 8px",
              borderRadius: 6,
              background: selectedIndex === index ? "rgba(122,162,255,0.15)" : "transparent"
            }}
          >
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
