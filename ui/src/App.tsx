import { useState } from "react";
import Projects from "./pages/Projects";
import Chat from "./pages/Chat";
import TeamBuilder from "./pages/TeamBuilder";
import RunConsole from "./pages/RunConsole";
import Settings from "./pages/Settings";

type Page = "projects" | "chat" | "team" | "run" | "settings";

const pages: Record<Page, { label: string; node: JSX.Element }> = {
  projects: { label: "Projects", node: <Projects /> },
  chat: { label: "Chat", node: <Chat /> },
  team: { label: "Team Builder", node: <TeamBuilder /> },
  run: { label: "Run Console", node: <RunConsole /> },
  settings: { label: "Settings", node: <Settings /> }
};

export default function App() {
  const [page, setPage] = useState<Page>("projects");

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
        {pages[page].node}
      </main>
    </div>
  );
}
