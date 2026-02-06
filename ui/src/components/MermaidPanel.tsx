import { useEffect, useMemo, useRef } from "react";

const DEFAULT_GRAPH = `flowchart LR
  intake[\"Intake\"] --> planning[\"Planning\"]
  planning --> execution[\"Execution\"]
  execution --> testing[\"Testing\"]
  testing --> review[\"Review\"]
  review --> release[\"Release\"]
`;

export default function MermaidPanel({ diagram }: { diagram?: string }) {
  const ref = useRef(null as HTMLDivElement | null);
  const source = useMemo(() => diagram ?? DEFAULT_GRAPH, [diagram]);

  useEffect(() => {
    const render = async () => {
      if (!ref.current) {
        return;
      }
      try {
        const mermaid = (await import("mermaid")).default;
        mermaid.initialize({ startOnLoad: false, theme: "dark" });
        const { svg } = await mermaid.render("workflow", source);
        ref.current.innerHTML = svg;
      } catch {
        ref.current.innerText = source;
      }
    };
    render();
  }, [source]);

  return (
    <div className="card">
      <h3>Workflow Diagram</h3>
      <div ref={ref} />
      <div className="muted">Mermaid diagram auto-renders if available.</div>
    </div>
  );
}
