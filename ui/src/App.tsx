import { useEffect, useState } from "react";
import Projects from "./pages/Projects";
import Chat from "./pages/Chat";
import TeamBuilder from "./pages/TeamBuilder";
import TeamSettings from "./pages/TeamSettings";
import RunConsole from "./pages/RunConsole";
import Settings from "./pages/Settings";

type Page = "projects" | "chat" | "team" | "teamsettings" | "run" | "settings";

const pages: Record<Page, { label: string; node: JSX.Element }> = {
  chat: { label: "Chat", node: <Chat /> },
  projects: { label: "Projects", node: <Projects /> },
  team: { label: "Team Builder", node: <TeamBuilder /> },
  teamsettings: { label: "Team Settings", node: <TeamSettings /> },
  run: { label: "Run Console", node: <RunConsole /> },
  settings: { label: "Settings", node: <Settings /> }
};

export default function App() {
  const [page, setPage] = useState("chat");
  const pageKey = page as Page;

  useEffect(() => {
    const stored = window.localStorage.getItem("overmind.page");
    if (stored && stored in pages) {
      setPage(stored as Page);
    }
  }, []);

  useEffect(() => {
    window.localStorage.setItem("overmind.page", page);
  }, [page]);

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
        {pages[pageKey].node}
      </main>
    </div>
  );
}
