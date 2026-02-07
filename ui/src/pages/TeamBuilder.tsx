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
  gender?: string | null;
  pronouns?: string | null;
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

type ModelInfo = {
  id: string;
  provider: string;
};

type RecommendedEntry = {
  models?: {
    text?: string[];
    code?: string[];
    image?: string[];
  };
  defaults?: {
    manager?: string | null;
    worker?: string | null;
    code?: string | null;
    image?: string | null;
  };
};

const FALLBACK_PRESETS: Preset[] = [
  {
    name: "small",
    roles: ["Product Owner", "Tech Lead", "Developer", "Developer", "QA Engineer", "Release Manager"]
  },
  {
    name: "medium",
    roles: [
      "Product Owner",
      "Delivery Manager",
      "Tech Lead",
      "Developer",
      "Developer",
      "Developer",
      "Developer",
      "QA Engineer",
      "QA Engineer",
      "Release Manager"
    ]
  },
  {
    name: "large",
    roles: [
      "Product Owner",
      "Delivery Manager",
      "Tech Lead",
      "Developer",
      "Developer",
      "Developer",
      "Developer",
      "Developer",
      "Developer",
      "Developer",
      "QA Engineer",
      "QA Engineer",
      "QA Engineer",
      "Release Manager"
    ]
  }
];

export default function TeamBuilder() {
  const [teams, setTeams] = useState([] as Team[]);
  const [agents, setAgents] = useState([] as AgentConfig[]);
  const [projectId, setProjectId] = useState(1);
  const [name, setName] = useState("Core Team");
  const [teamId, setTeamId] = useState(0);
  const [presetSize, setPresetSize] = useState("medium");
  const [presetProvider, setPresetProvider] = useState("auto");
  const [presetModel, setPresetModel] = useState("auto");
  const [presets, setPresets] = useState([] as Preset[]);
  const [models, setModels] = useState([] as ModelInfo[]);
  const [providers, setProviders] = useState([] as string[]);
  const [recommended, setRecommended] = useState({} as Record<string, RecommendedEntry>);
  const [error, setError] = useState(null as string | null);
  const [showAllAgents, setShowAllAgents] = useState(false);
  const [showAllModels, setShowAllModels] = useState(false);
  const [customCounts, setCustomCounts] = useState({
    "Product Owner": 1,
    "Delivery Manager": 1,
    "Tech Lead": 1,
    Developer: 4,
    "QA Engineer": 2,
    "Release Manager": 1
  });

  useEffect(() => {
    const load = async () => {
      let activeId = projectId;
      try {
        const active = (await apiGet("/projects/active")) as { id: number };
        activeId = active.id;
        setProjectId(active.id);
      } catch (err) {
        setError((err as Error).message);
      }
      try {
        const fetchedTeams = (await apiGet(`/teams?project_id=${activeId}`)) as Team[];
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
        const fetchedModels = (await apiGet("/models?only_enabled=true")) as ModelInfo[];
        setModels(fetchedModels);
        setProviders([...new Set(fetchedModels.map((item: ModelInfo) => item.provider))]);
        const rec = (await apiGet("/models/recommended?only_enabled=true")) as Record<
          string,
          RecommendedEntry
        >;
        setRecommended(rec);
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

  const refreshTeams = async () => {
    const data = (await apiGet(`/teams?project_id=${projectId}`)) as Team[];
    setTeams(data);
    if (data.length > 0 && data[0].id) {
      setTeamId(data[0].id);
    } else {
      setTeamId(0);
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
      const payload: Record<string, unknown> = {
        size: presetSize,
        provider: presetProvider,
        model: presetModel
      };
      if (presetSize === "custom") {
        payload.role_counts = customCounts;
      }
      await apiPost(`/teams/${teamId}/apply-preset`, payload);
      await refreshAgents();
      await refreshTeams();
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
        const payload: Record<string, unknown> = {
          size: presetSize,
          provider: presetProvider,
          model: presetModel
        };
        if (presetSize === "custom") {
          payload.role_counts = customCounts;
        }
        await apiPost(`/teams/${created.id}/apply-preset`, payload);
        await refreshAgents();
        await refreshTeams();
      }
    } catch (err) {
      setError((err as Error).message);
    }
  };

  const deleteTeam = async (id: number) => {
    setError(null);
    try {
      await apiDelete(`/teams/${id}`);
      await refreshTeams();
      await refreshAgents();
    } catch (err) {
      setError((err as Error).message);
    }
  };

  const updateAgentById = async (agentId: number) => {
    setError(null);
    const agent = agents.find((item: AgentConfig) => item.id === agentId);
    if (!agent) {
      return;
    }
    try {
      const updated = (await apiPut(`/agents/${agentId}`, agent)) as AgentConfig;
      setAgents((prev: AgentConfig[]) =>
        prev.map((item: AgentConfig) => (item.id === updated.id ? updated : item))
      );
    } catch (err) {
      setError((err as Error).message);
    }
  };

  const modelsForProvider = (providerName: string) =>
    models
      .filter((item: ModelInfo) => item.provider === providerName)
      .map((item: ModelInfo) => item.id);
  const hasProviders = providers.length > 0;

  const getRecommendedModels = (providerName: string, roleName: string) => {
    const entry = recommended?.[providerName];
    const available = entry?.models ?? {};
    const roleLower = roleName.toLowerCase();
    if (roleLower.includes("developer") || roleLower.includes("engineer") || roleLower.includes("tech")) {
      return available.code?.length ? available.code : available.text ?? [];
    }
    if (roleLower.includes("designer") || roleLower.includes("artist")) {
      return available.image?.length ? available.image : available.text ?? [];
    }
    return available.text ?? [];
  };

  const modelOptionsFor = (providerName: string, roleName: string, currentValue: string) => {
    const base = showAllModels
      ? modelsForProvider(providerName)
      : getRecommendedModels(providerName, roleName);
    const merged = [...base, currentValue].filter(Boolean);
    return Array.from(new Set(merged));
  };

  const presetModelOptions =
    presetProvider === "auto" ? [] : modelOptionsFor(presetProvider, "Manager", presetModel);
  const hasModelsForPreset = presetModelOptions.length > 0;

  const suggestModel = (roleName: string, providerName: string) => {
    const defaults = recommended?.[providerName]?.defaults;
    const roleLower = roleName.toLowerCase();
    if (defaults) {
      if (
        roleLower.includes("manager") ||
        roleLower.includes("owner") ||
        roleLower.includes("lead") ||
        roleLower.includes("architect") ||
        roleLower.includes("product") ||
        roleLower.includes("delivery") ||
        roleLower.includes("release")
      ) {
        return defaults.manager ?? defaults.worker ?? "gpt-4";
      }
      if (
        roleLower.includes("developer") ||
        roleLower.includes("engineer") ||
        roleLower.includes("tech")
      ) {
        return defaults.code ?? defaults.worker ?? "gpt-4";
      }
      if (roleLower.includes("designer") || roleLower.includes("artist")) {
        return defaults.image ?? defaults.worker ?? "gpt-4";
      }
      return defaults.worker ?? "gpt-4";
    }
    const available = modelsForProvider(providerName);
    if (!available.length) {
      return "gpt-4";
    }
    const wantsCode = roleLower.includes("developer") || roleLower.includes("tech lead");
    const wantsPlan =
      roleLower.includes("product owner") ||
      roleLower.includes("delivery") ||
      roleLower.includes("release") ||
      roleLower.includes("planner");
    if (wantsCode) {
      const codex = available.find((item: string) => item.toLowerCase().includes("codex"));
      if (codex) {
        return codex;
      }
      const codey = available.find((item: string) => item.toLowerCase().includes("code"));
      if (codey) {
        return codey;
      }
    }
    if (wantsPlan) {
      const max = available.find((item: string) => item.toLowerCase().includes("max"));
      if (max) {
        return max;
      }
    }
    return available[0];
  };

  const countRoles = (teamIdValue: number) => {
    const counts: Record<string, number> = {};
    agents
      .filter((agent: AgentConfig) => agent.team_id === teamIdValue)
      .forEach((agent: AgentConfig) => {
        counts[agent.role] = (counts[agent.role] ?? 0) + 1;
      });
    return counts;
  };

  const inferSizeLabel = (counts: Record<string, number>) => {
    const source = presets.length ? presets : FALLBACK_PRESETS;
    for (const preset of source) {
      const target: Record<string, number> = {};
      preset.roles.forEach((role: string) => {
        target[role] = (target[role] ?? 0) + 1;
      });
      const keys = new Set([...Object.keys(target), ...Object.keys(counts)]);
      let matches = true;
      keys.forEach((key) => {
        if ((target[key] ?? 0) !== (counts[key] ?? 0)) {
          matches = false;
        }
      });
      if (matches) {
        return preset.name;
      }
    }
    return "custom";
  };

  return (
    <section>
      <h2>Team Builder</h2>
      {error && <p style={{ color: "var(--danger)" }}>{error}</p>}
      <div className="card">
        <h3>Teams</h3>
        <ul>
          {teams.map((team: Team) => {
            const counts = team.id ? countRoles(team.id) : {};
            const sizeLabel = inferSizeLabel(counts);
            const total = Object.values(counts).reduce((sum, count) => sum + count, 0);
            const breakdown = Object.entries(counts)
              .map(([roleName, count]) => `${roleName}: ${count}`)
              .join(" · ");
            return (
              <li key={team.id}>
                <div className="row" style={{ alignItems: "center" }}>
                  <button
                    className={team.id === teamId ? "secondary" : "pill"}
                    onClick={() => team.id && setTeamId(team.id)}
                  >
                    {team.name}
                  </button>
                  <span className="pill">Project {team.project_id}</span>{" "}
                  <span className="pill">{sizeLabel}</span>{" "}
                  <span className="pill">{total} members</span>
                  {team.id && (
                    <button className="danger" onClick={() => deleteTeam(team.id as number)}>
                      Delete
                    </button>
                  )}
                </div>
                {breakdown && <div className="muted">{breakdown}</div>}
              </li>
            );
          })}
        </ul>
        <h4 style={{ marginTop: 16 }}>Team Setup</h4>
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
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="New team name"
          />
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
            <option value="custom">Custom</option>
          </select>
          {presetSize === "custom" && (
            <div className="row">
              {(Object.entries(customCounts) as [string, number][]).map(([roleName, count]) => (
                <label key={roleName} className="pill">
                  {roleName}
                  <input
                    type="number"
                    min={0}
                    value={count}
                    onChange={(e) =>
                      setCustomCounts((prev: typeof customCounts) => ({
                        ...prev,
                        [roleName]: Number(e.target.value)
                      }))
                    }
                    style={{ width: 72, marginLeft: 6 }}
                  />
                </label>
              ))}
            </div>
          )}
          {hasProviders ? (
            <select
              value={presetProvider}
              onChange={(e) => {
                const value = e.target.value;
                setPresetProvider(value);
                setPresetModel(value === "auto" ? "auto" : suggestModel("Developer", value));
              }}
            >
              <option value="auto">Auto</option>
              {providers.map((providerName: string) => (
                <option key={providerName} value={providerName}>
                  {providerName}
                </option>
              ))}
            </select>
          ) : (
            <input
              value={presetProvider}
              onChange={(e) => setPresetProvider(e.target.value)}
              placeholder="Provider"
            />
          )}
          {presetProvider === "auto" ? (
            <input value="auto" disabled />
          ) : hasModelsForPreset ? (
            <select value={presetModel} onChange={(e) => setPresetModel(e.target.value)}>
              {presetModelOptions.map((modelId: string) => (
                <option key={modelId} value={modelId}>
                  {modelId}
                </option>
              ))}
            </select>
          ) : (
            <input
              value={presetModel}
              onChange={(e) => setPresetModel(e.target.value)}
              placeholder="Model"
            />
          )}
          <button onClick={applyPreset} disabled={!teams.length}>
            Apply Preset
          </button>
          <button onClick={createTeamFromPreset}>
            Create Team + Apply
          </button>
        </div>
      </div>
      <div className="card">
        <h3>Agents {teamId ? `(Team #${teamId})` : ""}</h3>
        <div className="row" style={{ gap: 12, flexWrap: "wrap", marginBottom: 8 }}>
          <label className="pill">
            <input
              type="checkbox"
              checked={showAllAgents}
              onChange={(e) => setShowAllAgents(e.target.checked)}
              style={{ marginRight: 6 }}
            />
            Show all teams
          </label>
          <label className="pill">
            <input
              type="checkbox"
              checked={showAllModels}
              onChange={(e) => setShowAllModels(e.target.checked)}
              style={{ marginRight: 6 }}
            />
            Show all models (slow)
          </label>
        </div>
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
                    onBlur={() => agent.id && updateAgentById(agent.id)}
                    placeholder="Name"
                  />
                  <select
                    value={agent.gender ?? ""}
                    onChange={(e) =>
                      setAgents((prev: AgentConfig[]) =>
                        prev.map((item: AgentConfig) =>
                          item.id === agent.id
                            ? { ...item, gender: e.target.value }
                            : item
                        )
                      )
                    }
                    onBlur={() => agent.id && updateAgentById(agent.id)}
                  >
                    <option value="">Gender</option>
                    <option value="female">Female</option>
                    <option value="male">Male</option>
                    <option value="nonbinary">Non-binary</option>
                    <option value="other">Other</option>
                  </select>
                  <input
                    value={agent.pronouns ?? ""}
                    onChange={(e) =>
                      setAgents((prev: AgentConfig[]) =>
                        prev.map((item: AgentConfig) =>
                          item.id === agent.id
                            ? { ...item, pronouns: e.target.value }
                            : item
                        )
                      )
                    }
                    onBlur={() => agent.id && updateAgentById(agent.id)}
                    placeholder="Pronouns"
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
                    onBlur={() => agent.id && updateAgentById(agent.id)}
                    placeholder="Role"
                  />
                  {hasProviders ? (
                    <select
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
                      onBlur={() => agent.id && updateAgentById(agent.id)}
                    >
                      {providers.map((providerName: string) => (
                        <option key={providerName} value={providerName}>
                          {providerName}
                        </option>
                      ))}
                    </select>
                  ) : (
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
                      onBlur={() => agent.id && updateAgentById(agent.id)}
                      placeholder="Provider"
                    />
                  )}
                  {modelOptionsFor(agent.provider, agent.role, agent.model).length ? (
                    <select
                      value={agent.model}
                      onChange={(e) =>
                        setAgents((prev: AgentConfig[]) =>
                          prev.map((item: AgentConfig) =>
                            item.id === agent.id ? { ...item, model: e.target.value } : item
                          )
                        )
                      }
                      onBlur={() => agent.id && updateAgentById(agent.id)}
                    >
                      {modelOptionsFor(agent.provider, agent.role, agent.model).map(
                        (modelId: string) => (
                        <option key={modelId} value={modelId}>
                          {modelId}
                        </option>
                      )
                      )}
                    </select>
                  ) : (
                    <input
                      value={agent.model}
                      onChange={(e) =>
                        setAgents((prev: AgentConfig[]) =>
                          prev.map((item: AgentConfig) =>
                            item.id === agent.id ? { ...item, model: e.target.value } : item
                          )
                        )
                      }
                      onBlur={() => agent.id && updateAgentById(agent.id)}
                      placeholder="Model"
                    />
                  )}
                  <button onClick={() => agent.id && updateAgentById(agent.id)}>
                    Save
                  </button>
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
                  onBlur={() => agent.id && updateAgentById(agent.id)}
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
                    onBlur={() => agent.id && updateAgentById(agent.id)}
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
                    onBlur={() => agent.id && updateAgentById(agent.id)}
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
                  onBlur={() => agent.id && updateAgentById(agent.id)}
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
