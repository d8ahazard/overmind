import { useEffect, useState } from "react";
import { apiDelete, apiGet, apiPost, apiPut } from "../lib/api";

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
  permissions?: string | null;
  capabilities?: string | null;
};

type Preset = {
  name: string;
  roles: string[];
};

export default function TeamBuilder() {
  const [teams, setTeams] = useState([] as Team[]);
  const [agents, setAgents] = useState([] as AgentConfig[]);
  const [projectId, setProjectId] = useState(1);
  const [name, setName] = useState("Core Team");
  const [teamId, setTeamId] = useState(0);
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
  const [presets, setPresets] = useState([] as Preset[]);
  const [error, setError] = useState(null as string | null);
  const [showAllAgents, setShowAllAgents] = useState(false);

  useEffect(() => {
    const load = async () => {
      try {
        const active = (await apiGet("/projects/active")) as { id: number };
        setProjectId(active.id);
      } catch (err) {
        setError((err as Error).message);
      }
      try {
        const fetchedTeams = (await apiGet("/teams")) as Team[];
        setTeams(fetchedTeams);
        if (fetchedTeams.length > 0 && fetchedTeams[0].id) {
          setTeamId(fetchedTeams[0].id);
        } else {
          setTeamId(0);
        }
      } catch (err) {
        setError((err as Error).message);
      }
      try {
        const fetchedPresets = (await apiGet("/teams/presets")) as Preset[];
        setPresets(fetchedPresets);
      } catch (err) {
        setError((err as Error).message);
      }
      try {
        const fetchedAgents = (await apiGet("/agents")) as AgentConfig[];
        setAgents(fetchedAgents);
      } catch (err) {
        setError((err as Error).message);
      }
    };
    void load();
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
      if (created.id) {
        setTeamId(created.id);
      }
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
    if (!teamId || !teams.find((team: Team) => team.id === teamId)) {
      setError("Create or select a valid team before applying a preset.");
      return;
    }
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

  const createTeamFromPreset = async () => {
    setError(null);
    try {
      const created = (await apiPost("/teams", {
        project_id: projectId,
        name
      })) as Team;
      setTeams((prev: Team[]) => [...prev, created]);
      if (created.id) {
        setTeamId(created.id);
        await apiPost(`/teams/${created.id}/apply-preset`, {
          size: presetSize,
          provider: presetProvider,
          model: presetModel
        });
        await refreshAgents();
      }
    } catch (err) {
      setError((err as Error).message);
    }
  };

  const updateAgent = async (agent: AgentConfig) => {
    setError(null);
    if (!agent.id) {
      return;
    }
    try {
      const updated = (await apiPut(`/agents/${agent.id}`, agent)) as AgentConfig;
      setAgents((prev: AgentConfig[]) =>
        prev.map((item: AgentConfig) => (item.id === updated.id ? updated : item))
      );
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
          <label className="pill">Team</label>
          <select
            value={teamId}
            onChange={(e) => setTeamId(Number(e.target.value))}
          >
            <option value={0}>Select team</option>
            {teams.map((team: Team) => (
              <option key={team.id} value={team.id}>
                {team.name} (#{team.id})
              </option>
            ))}
          </select>
          <label className="pill">Preset</label>
          <select value={presetSize} onChange={(e) => setPresetSize(e.target.value)}>
            {presets.length ? (
              presets.map((preset: Preset) => (
                <option key={preset.name} value={preset.name}>
                  {preset.name} ({preset.roles.length} roles)
                </option>
              ))
            ) : (
              <>
                <option value="small">Small</option>
                <option value="medium">Medium</option>
                <option value="large">Large</option>
              </>
            )}
          </select>
          <input
            value={presetProvider}
            onChange={(e) => setPresetProvider(e.target.value)}
          />
          <input value={presetModel} onChange={(e) => setPresetModel(e.target.value)} />
          <button onClick={applyPreset} disabled={!teams.length}>
            Apply Preset
          </button>
          <button onClick={createTeamFromPreset}>
            Create Team + Apply
          </button>
        </div>
      </div>
      <div className="card">
        <h3>Add Agent</h3>
        <div className="row">
          <select
            value={teamId}
            onChange={(e) => setTeamId(Number(e.target.value))}
          >
            <option value={0}>Select team</option>
            {teams.map((team: Team) => (
              <option key={team.id} value={team.id}>
                {team.name} (#{team.id})
              </option>
            ))}
          </select>
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
        <label className="pill" style={{ marginBottom: 8 }}>
          <input
            type="checkbox"
            checked={showAllAgents}
            onChange={(e) => setShowAllAgents(e.target.checked)}
            style={{ marginRight: 6 }}
          />
          Show all teams
        </label>
        <ul>
          {agents
            .filter((agent: AgentConfig) =>
              showAllAgents ? true : agent.team_id === teamId
            )
            .map((agent: AgentConfig) => (
              <li key={agent.id}>
                <div className="row" style={{ alignItems: "center" }}>
                  {agent.avatar_url && (
                    <img
                      src={agent.avatar_url}
                      alt="avatar"
                      style={{ width: 28, height: 28, borderRadius: "999px", marginRight: 8 }}
                    />
                  )}
                  <input
                    value={agent.display_name ?? ""}
                    onChange={(e) =>
                      setAgents((prev: AgentConfig[]) =>
                        prev.map((item: AgentConfig) =>
                          item.id === agent.id
                            ? { ...item, display_name: e.target.value }
                            : item
                        )
                      )
                    }
                    placeholder="Name"
                  />
                  <input
                    value={agent.role}
                    onChange={(e) =>
                      setAgents((prev: AgentConfig[]) =>
                        prev.map((item: AgentConfig) =>
                          item.id === agent.id ? { ...item, role: e.target.value } : item
                        )
                      )
                    }
                    placeholder="Role"
                  />
                  <input
                    value={agent.provider}
                    onChange={(e) =>
                      setAgents((prev: AgentConfig[]) =>
                        prev.map((item: AgentConfig) =>
                          item.id === agent.id
                            ? { ...item, provider: e.target.value }
                            : item
                        )
                      )
                    }
                    placeholder="Provider"
                  />
                  <input
                    value={agent.model}
                    onChange={(e) =>
                      setAgents((prev: AgentConfig[]) =>
                        prev.map((item: AgentConfig) =>
                          item.id === agent.id ? { ...item, model: e.target.value } : item
                        )
                      )
                    }
                    placeholder="Model"
                  />
                  <button onClick={() => updateAgent(agent)}>Save</button>
                  {agent.id && (
                    <button
                      onClick={() => deleteAgent(agent.id as number)}
                      className="danger"
                      style={{ marginLeft: 8 }}
                    >
                      Delete
                    </button>
                  )}
                </div>
                <textarea
                  value={agent.personality ?? ""}
                  onChange={(e) =>
                    setAgents((prev: AgentConfig[]) =>
                      prev.map((item: AgentConfig) =>
                        item.id === agent.id
                          ? { ...item, personality: e.target.value }
                          : item
                      )
                    )
                  }
                  placeholder="Personality"
                  style={{ marginTop: 8, width: "100%" }}
                />
                <div className="row" style={{ marginTop: 8 }}>
                  <input
                    value={agent.permissions ?? ""}
                    onChange={(e) =>
                      setAgents((prev: AgentConfig[]) =>
                        prev.map((item: AgentConfig) =>
                          item.id === agent.id
                            ? { ...item, permissions: e.target.value }
                            : item
                        )
                      )
                    }
                    placeholder="Permissions"
                  />
                  <input
                    value={agent.capabilities ?? ""}
                    onChange={(e) =>
                      setAgents((prev: AgentConfig[]) =>
                        prev.map((item: AgentConfig) =>
                          item.id === agent.id
                            ? { ...item, capabilities: e.target.value }
                            : item
                        )
                      )
                    }
                    placeholder="Capabilities"
                  />
                </div>
                <input
                  value={agent.avatar_url ?? ""}
                  onChange={(e) =>
                    setAgents((prev: AgentConfig[]) =>
                      prev.map((item: AgentConfig) =>
                        item.id === agent.id
                          ? { ...item, avatar_url: e.target.value }
                          : item
                      )
                    )
                  }
                  placeholder="Avatar URL"
                  style={{ marginTop: 8, width: "100%" }}
                />
              </li>
            ))}
        </ul>
        {!agents.filter((agent: AgentConfig) => agent.team_id === teamId).length && !showAllAgents && (
          <p className="muted">No agents for the selected team yet.</p>
        )}
      </div>
    </section>
  );
}
