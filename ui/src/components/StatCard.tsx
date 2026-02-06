type Stat = {
  label: string;
  value: string;
  trend?: string;
};

export default function StatCard({ stat }: { stat: Stat }) {
  return (
    <div className="card">
      <div className="muted">{stat.label}</div>
      <h2 style={{ margin: "6px 0" }}>{stat.value}</h2>
      {stat.trend && <div className="pill">{stat.trend}</div>}
    </div>
  );
}
