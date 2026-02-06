import { useState } from "react";
import GlassCard from "../components/GlassCard";
import { apiPost } from "../lib/api";

export default function NewProjectWizard() {
  const [name, setName] = useState("New Project");
  const [path, setPath] = useState("E:\\dev\\StandYourGround");
  const [teamName, setTeamName] = useState("Core Team");
  const [preset, setPreset] = useState("medium");
  const [provider, setProvider] = useState("openai");
  const [model, setModel] = useState("gpt-4");
  const [framework, setFramework] = useState("Scrum");
  const [status, setStatus] = useState("");

  const createProject = async () => {
    const project = (await apiPost("/projects", {
      name,
      repo_local_path: path,
      team_framework: framework
    })) as { id: number };
    await apiPost(`/projects/${project.id}/activate`, {});
    const team = (await apiPost("/teams", {
      project_id: project.id,
      name: teamName
    })) as { id: number };
    await apiPost(`/teams/${team.id}/apply-preset`, {
      size: preset,
      provider,
      model
    });
    setStatus("Project created and team configured.");
  };

  return (
    <section>
      <div className="page-header">
        <div>
          <div className="page-title">New Project Wizard</div>
          <div className="page-subtitle">Project + team setup in one flow</div>
        </div>
      </div>
      <GlassCard title="Project Details">
        <div className="row">
          <input value={name} onChange={(e) => setName(e.target.value)} />
          <input value={path} onChange={(e) => setPath(e.target.value)} />
          <select value={framework} onChange={(e) => setFramework(e.target.value)}>
            <option value="Scrum">Scrum</option>
            <option value="Agile">Agile</option>
            <option value="Kanban">Kanban</option>
            <option value="Freeform">Freeform</option>
            <option value="Other">Other</option>
          </select>
        </div>
      </GlassCard>
      <GlassCard title="Team Setup">
        <div className="row">
          <input value={teamName} onChange={(e) => setTeamName(e.target.value)} />
          <select value={preset} onChange={(e) => setPreset(e.target.value)}>
            <option value="small">Small</option>
            <option value="medium">Medium</option>
            <option value="large">Large</option>
          </select>
          <input value={provider} onChange={(e) => setProvider(e.target.value)} />
          <input value={model} onChange={(e) => setModel(e.target.value)} />
          <button onClick={createProject}>Create Project</button>
        </div>
        {status && <div className="muted">{status}</div>}
      </GlassCard>
    </section>
  );
}
