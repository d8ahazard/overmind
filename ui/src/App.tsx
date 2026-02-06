import { useEffect, useState } from "react";
import Projects from "./pages/Projects";
import Chat from "./pages/Chat";
import TeamBuilder from "./pages/TeamBuilder";
import RunConsole from "./pages/RunConsole";
import Settings from "./pages/Settings";
import Wizard from "./pages/Wizard";
import NewProjectWizard from "./pages/NewProjectWizard";
import { apiGet } from "./lib/api";

type Page = "projects" | "chat" | "team" | "run" | "settings" | "wizard" | "newproject";

const pages: Record<Page, { label: string; node: JSX.Element }> = {
  projects: { label: "Projects", node: <Projects /> },
  newproject: { label: "New Project", node: <NewProjectWizard /> },
  chat: { label: "Chat", node: <Chat /> },
  team: { label: "Team Builder", node: <TeamBuilder /> },
  run: { label: "Run Console", node: <RunConsole /> },
  settings: { label: "Settings", node: <Settings /> },
  wizard: { label: "Wizard", node: <Wizard /> }
};

export default function App() {
  const [page, setPage] = useState<Page>("projects");
  const [showWizard, setShowWizard] = useState(false);

  useEffect(() => {
    apiGet("/keys")
      .then((data) => {
        const keys = data as { has_key: boolean }[];
        const hasAny = keys.some((item) => item.has_key);
        setShowWizard(!hasAny);
      })
      .catch(() => setShowWizard(true));
  }, []);

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <h1>Overmind</h1>
        {Object.entries(pages).map(([key, entry]) => (
          <button
            key={key}
            className={`nav-button ${page === key ? "active" : ""}`}
            onClick={() => setPage(key as Page)}
          >
            {entry.label}
          </button>
        ))}
      </aside>
      <main className="content">
        {showWizard && page !== "wizard" && (
          <div className="card glow" style={{ marginBottom: 16 }}>
            <div className="row space">
              <div>
                <div className="page-title">Setup Required</div>
                <div className="page-subtitle">
                  Add API keys to unlock providers and models.
                </div>
              </div>
              <button onClick={() => setPage("wizard")}>Open Wizard</button>
            </div>
          </div>
        )}
        {pages[page].node}
      </main>
    </div>
  );
}
