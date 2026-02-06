import { useEffect, useState } from "react";
import { apiDelete, apiGet, apiPost } from "../lib/api";

type Team = {
  id?: number;
  project_id: number;
  name: string;
};

type AgentConfig = {
  id?: number;
  team_id: number;
  role: string;
  display_name?: string | null;
  personality?: string | null;
  avatar_url?: string | null;
  provider: string;
  model: string;
};

export default function TeamBuilder() {
  const [teams, setTeams] = useState([] as Team[]);
  const [agents, setAgents] = useState([] as AgentConfig[]);
  const [projectId, setProjectId] = useState(1);
  const [name, setName] = useState("Core Team");
  const [teamId, setTeamId] = useState(1);
  const [displayName, setDisplayName] = useState("Alex");
  const [role, setRole] = useState("Developer");
  const [personality, setPersonality] = useState(
    "Practical, curious, and focused on clean, working code."
  );
  const [avatarUrl, setAvatarUrl] = useState("");
  const [provider, setProvider] = useState("openai");
  const [model, setModel] = useState("gpt-4");
  const [presetSize, setPresetSize] = useState("medium");
  const [presetProvider, setPresetProvider] = useState("openai");
  const [presetModel, setPresetModel] = useState("gpt-4");
  const [error, setError] = useState(null as string | null);

  useEffect(() => {
    apiGet("/teams")
      .then(setTeams)
      .catch((err) => setError(err.message));
    apiGet("/agents")
      .then(setAgents)
      .catch((err) => setError(err.message));
  }, []);

  const refreshAgents = async () => {
    const data = (await apiGet("/agents")) as AgentConfig[];
    setAgents(data);
  };

  const createTeam = async () => {
    setError(null);
    try {
      const created = (await apiPost("/teams", {
        project_id: projectId,
        name
      })) as Team;
      setTeams((prev: Team[]) => [...prev, created]);
    } catch (err) {
      setError((err as Error).message);
    }
  };

  const createAgent = async () => {
    setError(null);
    try {
      const created = (await apiPost("/agents", {
        team_id: teamId,
        display_name: displayName,
        role,
        personality,
        avatar_url: avatarUrl || null,
        provider,
        model
      })) as AgentConfig;
      setAgents((prev: AgentConfig[]) => [...prev, created]);
    } catch (err) {
      setError((err as Error).message);
    }
  };

  const deleteAgent = async (agentId: number) => {
    setError(null);
    try {
      await apiDelete(`/agents/${agentId}`);
      setAgents((prev: AgentConfig[]) =>
        prev.filter((agent: AgentConfig) => agent.id !== agentId)
      );
    } catch (err) {
      setError((err as Error).message);
    }
  };

  const applyPreset = async () => {
    setError(null);
    try {
      await apiPost(`/teams/${teamId}/apply-preset`, {
        size: presetSize,
        provider: presetProvider,
        model: presetModel
      });
      await refreshAgents();
    } catch (err) {
      setError((err as Error).message);
    }
  };

  return (
    <section>
      <h2>Team Builder</h2>
      <div className="card">
        <h3>Create Team</h3>
        <div className="row">
          <input
            type="number"
            value={projectId}
            onChange={(e) => setProjectId(Number(e.target.value))}
          />
          <input value={name} onChange={(e) => setName(e.target.value)} />
          <button onClick={createTeam}>Create</button>
        </div>
      </div>
      {error && <p style={{ color: "var(--danger)" }}>{error}</p>}
      <div className="card">
        <h3>Teams</h3>
        <ul>
          {teams.map((team: Team) => (
            <li key={team.id}>
              {team.name} <span className="pill">Project {team.project_id}</span>
            </li>
          ))}
        </ul>
      </div>
      <div className="card">
        <h3>Apply Team Preset</h3>
        <div className="row">
          <label className="pill">Preset</label>
          <select value={presetSize} onChange={(e) => setPresetSize(e.target.value)}>
            <option value="small">Small</option>
            <option value="medium">Medium</option>
            <option value="large">Large</option>
          </select>
          <input
            value={presetProvider}
            onChange={(e) => setPresetProvider(e.target.value)}
          />
          <input value={presetModel} onChange={(e) => setPresetModel(e.target.value)} />
          <button onClick={applyPreset}>Apply Preset</button>
        </div>
      </div>
      <div className="card">
        <h3>Add Agent</h3>
        <div className="row">
          <input
            type="number"
            value={teamId}
            onChange={(e) => setTeamId(Number(e.target.value))}
          />
          <input
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            placeholder="Name"
          />
          <input value={role} onChange={(e) => setRole(e.target.value)} />
          <input
            value={personality}
            onChange={(e) => setPersonality(e.target.value)}
            placeholder="Personality"
          />
        <input
          value={avatarUrl}
          onChange={(e) => setAvatarUrl(e.target.value)}
          placeholder="Avatar URL"
        />
          <input value={provider} onChange={(e) => setProvider(e.target.value)} />
          <input value={model} onChange={(e) => setModel(e.target.value)} />
          <button onClick={createAgent}>Add Agent</button>
        </div>
      </div>
      <div className="card">
        <h3>Agents</h3>
        <ul>
          {agents.map((agent: AgentConfig) => (
            <li key={agent.id}>
            {agent.avatar_url && (
              <img
                src={agent.avatar_url}
                alt="avatar"
                style={{ width: 28, height: 28, borderRadius: "999px", marginRight: 8 }}
              />
            )}
              {agent.display_name ?? agent.role} ({agent.role}) - {agent.provider}/{agent.model}{" "}
              <span className="pill">Team {agent.team_id}</span>
              {agent.personality && (
                <div className="muted">{agent.personality}</div>
              )}
              {agent.id && (
                <button
                  onClick={() => deleteAgent(agent.id as number)}
                  className="danger"
                  style={{ marginLeft: 8 }}
                >
                  Delete
                </button>
              )}
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
