export default function BoardSummary() {
  return (
    <div className="card">
      <h3>Board Summary</h3>
      <div className="grid-2">
        <div>
          <div className="muted">Backlog</div>
          <div style={{ fontSize: 20 }}>14</div>
        </div>
        <div>
          <div className="muted">In Progress</div>
          <div style={{ fontSize: 20 }}>6</div>
        </div>
        <div>
          <div className="muted">In Review</div>
          <div style={{ fontSize: 20 }}>3</div>
        </div>
        <div>
          <div className="muted">Done</div>
          <div style={{ fontSize: 20 }}>9</div>
        </div>
      </div>
    </div>
  );
}
