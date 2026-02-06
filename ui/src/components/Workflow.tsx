type Step = {
  label: string;
  status: "done" | "active" | "pending";
};

export default function Workflow({ steps }: { steps: Step[] }) {
  return (
    <div className="card">
      <h3>Workflow</h3>
      <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
        {steps.map((step) => (
          <div
            key={step.label}
            className="pill"
            style={{
              background:
                step.status === "done"
                  ? "rgba(87,217,163,0.2)"
                  : step.status === "active"
                  ? "rgba(122,162,255,0.25)"
                  : "rgba(18,24,38,0.8)",
              borderColor:
                step.status === "active"
                  ? "rgba(122,162,255,0.5)"
                  : "rgba(122,162,255,0.18)"
            }}
          >
            {step.label}
          </div>
        ))}
      </div>
    </div>
  );
}
