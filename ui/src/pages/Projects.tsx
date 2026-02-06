import { useEffect, useState } from "react";
import { apiGet, apiPost } from "../lib/api";

type Project = {
  id?: number;
  name: string;
  repo_local_path: string;
  repo_url?: string | null;
};

export default function Projects() {
  const [projects, setProjects] = useState([] as Project[]);
  const [activeId, setActiveId] = useState(null as number | null);
  const [name, setName] = useState("StandYourGround");
  const [path, setPath] = useState("E:\\dev\\StandYourGround");
  const [error, setError] = useState(null as string | null);

  useEffect(() => {
    apiGet("/projects")
      .then(setProjects)
      .catch((err) => setError(err.message));
    apiGet("/projects/active")
      .then((active) => setActiveId((active as Project).id ?? null))
      .catch(() => setActiveId(null));
  }, []);

  const createProject = async () => {
    setError(null);
    try {
      const created = (await apiPost("/projects", {
        name,
        repo_local_path: path
      })) as Project;
      setProjects((prev: Project[]) => [...prev, created]);
    } catch (err) {
      setError((err as Error).message);
    }
  };

  const activateProject = async (projectId: number) => {
    setError(null);
    try {
      await apiPost(`/projects/${projectId}/activate`, {});
      setActiveId(projectId);
    } catch (err) {
      setError((err as Error).message);
    }
  };

  return (
    <section>
      <h2>Projects</h2>
      <div className="card">
        <div className="row">
          <input value={name} onChange={(e) => setName(e.target.value)} />
          <input value={path} onChange={(e) => setPath(e.target.value)} />
          <button onClick={createProject}>Create</button>
        </div>
        {error && <p style={{ color: "var(--danger)" }}>{error}</p>}
      </div>
      <div className="card">
        <h3>Active Projects</h3>
        <ul>
          {projects.map((project: Project) => (
            <li key={project.id}>
              {project.name} <span className="pill">{project.repo_local_path}</span>
              {activeId === project.id ? (
                <span className="pill" style={{ marginLeft: 8 }}>
                  Active
                </span>
              ) : (
                <button
                  className="secondary"
                  style={{ marginLeft: 8 }}
                  onClick={() => activateProject(project.id as number)}
                >
                  Set Active
                </button>
              )}
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
