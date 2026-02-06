type Point = {
  label: string;
  value: number;
};

export function BarChart({ title, points }: { title: string; points: Point[] }) {
  const max = Math.max(1, ...points.map((point) => point.value));
  return (
    <div className="card">
      <h3>{title}</h3>
      <div style={{ display: "grid", gap: 8 }}>
        {points.map((point) => (
          <div key={point.label}>
            <div className="row" style={{ justifyContent: "space-between" }}>
              <span>{point.label}</span>
              <span className="pill">{point.value}</span>
            </div>
            <div
              style={{
                height: 8,
                background: "rgba(122,162,255,0.15)",
                borderRadius: 6,
                overflow: "hidden",
                marginTop: 4
              }}
            >
              <div
                style={{
                  width: `${(point.value / max) * 100}%`,
                  height: "100%",
                  background: "linear-gradient(90deg,#7aa2ff,#57d9a3)"
                }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export function StatRow({ title, stats }: { title: string; stats: { label: string; value: string }[] }) {
  return (
    <div className="card">
      <h3>{title}</h3>
      <div className="grid-2">
        {stats.map((stat) => (
          <div key={stat.label}>
            <div className="muted">{stat.label}</div>
            <div style={{ fontSize: 20, fontWeight: 600 }}>{stat.value}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
