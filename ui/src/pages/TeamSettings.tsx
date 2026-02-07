import { useEffect, useMemo, useState } from "react";
import { apiDelete, apiGet, apiPost, apiPut } from "../lib/api";

type Project = {
  id?: number;
  name: string;
  repo_local_path: string;
  repo_url?: string | null;
};

type ProjectSettings = {
  project_id: number;
  allow_all_tools: boolean;
  allow_high_risk: boolean;
  default_tool_scopes?: string | null;
  role_tool_scopes?: string | null;
  allow_pm_merge?: boolean | null;
  auto_execute_edits?: boolean | null;
  require_pm_pr_approval?: boolean | null;
  chat_target_policy?: string | null;
  task_retry_limit?: number | null;
  model_defaults?: string | null;
  memory_profiles?: string | null;
  mcp_endpoints?: string | null;
  mcp_ports?: string | null;
  enabled_plugins?: string | null;
};

type ProviderKey = {
  id?: number;
  provider: string;
  has_key: boolean;
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

type PersonalityTemplate = {
  id?: number;
  role: string;
  name: string;
  script: string;
};

type McpEndpointInfo = {
  url: string;
  tools: { name: string }[];
};

type RoleModelDefault = {
  provider: string;
  model: string;
};

type MemoryProfile = {
  cap: number;
  strategy: string;
};

type AgentInfo = {
  id?: number;
  display_name?: string | null;
  role: string;
};

type GoalInfo = {
  id: number;
  title: string;
  status: string;
};

type PluginInfo = {
  id: string;
  name: string;
};

const ROLE_OPTIONS = [
  "Product Owner",
  "Delivery Manager",
  "Tech Lead",
  "Developer",
  "QA Engineer",
  "Release Manager"
];

const ROLE_SCOPE_DEFAULTS: Record<string, string> = {
  "Product Owner": "system:run,file:read,file:write,git:status,git:diff,git:branch,git:commit,git:pr",
  "Delivery Manager": "system:run,file:read,file:write,git:status,git:diff,git:branch,git:commit,git:pr",
  "Tech Lead": "system:run,file:read,file:write,git:status,git:diff,git:branch,git:commit,git:pr",
  Developer: "system:run,file:read,file:write,git:status,git:diff,git:branch,git:commit,git:pr",
  "QA Engineer": "system:run,file:read,git:status,git:diff",
  "Release Manager": "system:run,file:read,file:write,git:status,git:diff,git:branch,git:commit,git:pr"
};

const MEMORY_STRATEGIES = ["rolling", "latest", "none"];

const parseJson = <T,>(raw: string | null | undefined, fallback: T): T => {
  if (!raw) {
    return fallback;
  }
  try {
    return JSON.parse(raw) as T;
  } catch {
    return fallback;
  }
};

export default function TeamSettings() {
  const [projects, setProjects] = useState([] as Project[]);
  const [activeId, setActiveId] = useState(null as number | null);
  const [name, setName] = useState("StandYourGround");
  const [path, setPath] = useState("E:\\dev\\StandYourGround");
  const [error, setError] = useState(null as string | null);

  const [projectSettings, setProjectSettings] = useState(null as ProjectSettings | null);
  const [modelDefaults, setModelDefaults] = useState({} as Record<string, RoleModelDefault>);
  const [memoryProfiles, setMemoryProfiles] = useState({} as Record<string, MemoryProfile>);
  const [roleToolScopes, setRoleToolScopes] = useState({} as Record<string, string>);
  const [modelRoleName, setModelRoleName] = useState("");
  const [memoryRoleName, setMemoryRoleName] = useState("");

  const [models, setModels] = useState([] as ModelInfo[]);
  const [providersByKey, setProvidersByKey] = useState([] as string[]);
  const [recommended, setRecommended] = useState({} as Record<string, RecommendedEntry>);
  const [showAllModels, setShowAllModels] = useState(false);

  const [providerKeys, setProviderKeys] = useState([] as ProviderKey[]);
  const [providerName, setProviderName] = useState("openai");
  const [providerValue, setProviderValue] = useState("");
  const [availableProviders, setAvailableProviders] = useState([] as { id: string; name: string }[]);
  const [plugins, setPlugins] = useState([] as PluginInfo[]);
  const [enabledPlugins, setEnabledPlugins] = useState([] as string[]);

  const [templates, setTemplates] = useState([] as PersonalityTemplate[]);
  const [templateRole, setTemplateRole] = useState("Developer");
  const [templateName, setTemplateName] = useState("Default");
  const [templateScript, setTemplateScript] = useState(
    "Practical, curious, and focused on clean, working code."
  );
  const [agents, setAgents] = useState([] as AgentInfo[]);
  const [memoryCounts, setMemoryCounts] = useState({} as Record<number, number>);
  const [goals, setGoals] = useState([] as GoalInfo[]);
  const [goalTitle, setGoalTitle] = useState("");

  const [mcpManual, setMcpManual] = useState([] as string[]);
  const [mcpDiscovered, setMcpDiscovered] = useState([] as McpEndpointInfo[]);
  const [mcpPorts, setMcpPorts] = useState([] as number[]);
  const [mcpUrl, setMcpUrl] = useState("");
  const [mcpPortsInput, setMcpPortsInput] = useState("");

  useEffect(() => {
    apiGet("/projects")
      .then(setProjects)
      .catch((err) => setError(err.message));
    apiGet("/projects/active")
      .then((active) => setActiveId((active as Project).id ?? null))
      .catch(() => setActiveId(null));
    apiGet("/projects/settings")
      .then((data) => setProjectSettings(data as ProjectSettings))
      .catch((err) => setError(err.message));
    apiGet<ModelInfo[]>("/models?only_enabled=true")
      .then((data) => {
        setModels(data);
        setProvidersByKey([...new Set(data.map((item: ModelInfo) => item.provider))]);
      })
      .catch((err) => setError(err.message));
    apiGet("/models/recommended?only_enabled=true")
      .then((data) => setRecommended(data as Record<string, RecommendedEntry>))
      .catch((err) => setError(err.message));
    apiGet("/keys")
      .then((data) => setProviderKeys(data as ProviderKey[]))
      .catch((err) => setError(err.message));
    apiGet("/providers")
      .then((data) => setAvailableProviders(data as { id: string; name: string }[]))
      .catch((err) => setError(err.message));
    apiGet("/providers/plugins")
      .then((data) => setPlugins(data as { id: string; name: string }[]))
      .catch((err) => setError(err.message));
    apiGet("/personalities")
      .then((data) => setTemplates(data as PersonalityTemplate[]))
      .catch((err) => setError(err.message));
    apiGet("/goals")
      .then((data) => setGoals(data as { id: number; title: string; status: string }[]))
      .catch((err) => setError(err.message));
    apiGet("/agents")
      .then((data) => setAgents(data as AgentInfo[]))
      .catch((err) => setError(err.message));
    apiGet("/memories")
      .then((data) => {
        const counts: Record<number, number> = {};
        (data as { agent_id?: number }[]).forEach((entry) => {
          if (!entry.agent_id) {
            return;
          }
          counts[entry.agent_id] = (counts[entry.agent_id] ?? 0) + 1;
        });
        setMemoryCounts(counts);
      })
      .catch((err) => setError(err.message));
    apiGet("/mcp/endpoints")
      .then((data) => {
        const payload = data as {
          manual_endpoints: string[];
          ports: number[];
          discovered: McpEndpointInfo[];
        };
        setMcpManual(payload.manual_endpoints ?? []);
        setMcpPorts(payload.ports ?? []);
        setMcpDiscovered(payload.discovered ?? []);
        setMcpPortsInput((payload.ports ?? []).join(","));
      })
      .catch((err) => setError(err.message));
  }, []);

  useEffect(() => {
    if (!projectSettings) {
      return;
    }
    const parsedDefaults = parseJson<Record<string, RoleModelDefault>>(
      projectSettings.model_defaults,
      {}
    );
    setModelDefaults(parsedDefaults);
    const parsedProfiles = parseJson<Record<string, MemoryProfile>>(
      projectSettings.memory_profiles,
      {}
    );
    setMemoryProfiles(parsedProfiles);
    const parsedRoleScopes = parseJson<Record<string, string>>(
      projectSettings.role_tool_scopes,
      {}
    );
    setRoleToolScopes(parsedRoleScopes);
    const parsedPlugins = parseJson<string[]>(projectSettings.enabled_plugins, []);
    setEnabledPlugins(parsedPlugins);
  }, [projectSettings]);

  useEffect(() => {
    if (Object.keys(modelDefaults).length > 0 || providersByKey.length === 0) {
      return;
    }
    const provider = providersByKey[0];
    const next: Record<string, RoleModelDefault> = {};
    ROLE_OPTIONS.forEach((role) => {
      const entry = recommended?.[provider]?.defaults;
      const roleLower = role.toLowerCase();
      let model = entry?.worker || "";
      if (roleLower.includes("developer") || roleLower.includes("engineer")) {
        model = entry?.code || model;
      } else if (
        roleLower.includes("manager") ||
        roleLower.includes("owner") ||
        roleLower.includes("lead") ||
        roleLower.includes("release")
      ) {
        model = entry?.manager || model;
      }
      next[role] = { provider, model };
    });
    setModelDefaults(next);
  }, [modelDefaults, providersByKey, recommended]);

  useEffect(() => {
    if (Object.keys(memoryProfiles).length > 0) {
      return;
    }
    const next: Record<string, MemoryProfile> = {};
    ROLE_OPTIONS.forEach((role) => {
      next[role] = { cap: 5, strategy: "rolling" };
    });
    setMemoryProfiles(next);
  }, [memoryProfiles]);

  useEffect(() => {
    if (Object.keys(roleToolScopes).length > 0) {
      return;
    }
    const next: Record<string, string> = {};
    ROLE_OPTIONS.forEach((role) => {
      next[role] = ROLE_SCOPE_DEFAULTS[role] ?? "system:run";
    });
    setRoleToolScopes(next);
  }, [roleToolScopes]);

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
      const settings = (await apiGet("/projects/settings")) as ProjectSettings;
      setProjectSettings(settings);
    } catch (err) {
      setError((err as Error).message);
    }
  };

  const updateProjectSettings = async (next: Partial<ProjectSettings>) => {
    setError(null);
    try {
      const updated = (await apiPut("/projects/settings", next)) as ProjectSettings;
      setProjectSettings(updated);
    } catch (err) {
      setError((err as Error).message);
    }
  };

  const upsertKey = async () => {
    setError(null);
    try {
      await apiPost("/keys", { provider: providerName, key: providerValue });
      const data = (await apiGet("/keys")) as ProviderKey[];
      setProviderKeys(data);
      setProviderValue("");
    } catch (err) {
      setError((err as Error).message);
    }
  };

  const deleteKey = async (provider: string) => {
    setError(null);
    try {
      await apiDelete(`/keys/${provider}`);
      const data = (await apiGet("/keys")) as ProviderKey[];
      setProviderKeys(data);
    } catch (err) {
      setError((err as Error).message);
    }
  };

  const createTemplate = async () => {
    setError(null);
    try {
      const created = (await apiPost("/personalities", {
        role: templateRole,
        name: templateName,
        script: templateScript
      })) as PersonalityTemplate;
      setTemplates((prev: PersonalityTemplate[]) => [...prev, created]);
    } catch (err) {
      setError((err as Error).message);
    }
  };

  const deleteTemplate = async (templateId: number) => {
    setError(null);
    try {
      await apiDelete(`/personalities/${templateId}`);
      setTemplates((prev: PersonalityTemplate[]) =>
        prev.filter((template: PersonalityTemplate) => template.id !== templateId)
      );
    } catch (err) {
      setError((err as Error).message);
    }
  };

  const refreshMcp = async () => {
    setError(null);
    try {
      await apiPost("/mcp/refresh", {});
      const data = (await apiGet("/mcp/endpoints")) as {
        manual_endpoints: string[];
        ports: number[];
        discovered: McpEndpointInfo[];
      };
      setMcpManual(data.manual_endpoints ?? []);
      setMcpPorts(data.ports ?? []);
      setMcpDiscovered(data.discovered ?? []);
      setMcpPortsInput((data.ports ?? []).join(","));
    } catch (err) {
      setError((err as Error).message);
    }
  };

  const addMcpEndpoint = async () => {
    setError(null);
    if (!mcpUrl.trim()) {
      return;
    }
    try {
      const data = (await apiPost("/mcp/endpoints", { url: mcpUrl.trim() })) as {
        endpoints: string[];
      };
      setMcpManual(data.endpoints ?? []);
      setMcpUrl("");
    } catch (err) {
      setError((err as Error).message);
    }
  };

  const removeMcpEndpoint = async (url: string) => {
    setError(null);
    try {
      const data = (await apiDelete(`/mcp/endpoints?url=${encodeURIComponent(url)}`)) as {
        endpoints: string[];
      };
      setMcpManual(data.endpoints ?? []);
    } catch (err) {
      setError((err as Error).message);
    }
  };

  const createGoal = async () => {
    const title = goalTitle.trim();
    if (!title) {
      return;
    }
    setError(null);
    try {
      const created = (await apiPost("/goals", { title })) as {
        id: number;
        title: string;
        status: string;
      };
      setGoals((prev: GoalInfo[]) => [...prev, created]);
      setGoalTitle("");
    } catch (err) {
      setError((err as Error).message);
    }
  };

  const updateGoalStatus = async (goalId: number, status: string) => {
    setError(null);
    try {
      const updated = (await apiPut(`/goals/${goalId}`, { status })) as {
        id: number;
        title: string;
        status: string;
      };
      setGoals((prev: GoalInfo[]) =>
        prev.map((goal: GoalInfo) => (goal.id === goalId ? updated : goal))
      );
    } catch (err) {
      setError((err as Error).message);
    }
  };

  const updateMcpPorts = async () => {
    setError(null);
    const parts = mcpPortsInput
      .split(",")
      .map((item: string) => item.trim())
      .filter(Boolean);
    const ports = parts
      .map((item: string) => Number(item))
      .filter((item: number) => !Number.isNaN(item));
    try {
      const data = (await apiPost("/mcp/ports", { ports })) as { ports: number[] };
      setMcpPorts(data.ports ?? []);
    } catch (err) {
      setError((err as Error).message);
    }
  };

  const modelOptionsFor = (providerName: string, roleName: string, currentValue: string) => {
    const filtered = models
      .filter((item: ModelInfo) => item.provider === providerName)
      .map((item: ModelInfo) => item.id);
    const entry = recommended?.[providerName];
    const available = entry?.models ?? {};
    const roleLower = roleName.toLowerCase();
    let base = available.text ?? [];
    if (roleLower.includes("developer") || roleLower.includes("engineer") || roleLower.includes("tech")) {
      base = available.code?.length ? available.code : base;
    } else if (roleLower.includes("designer") || roleLower.includes("artist")) {
      base = available.image?.length ? available.image : base;
    }
    const choices = showAllModels ? filtered : base;
    const merged = [...choices, currentValue].filter(Boolean);
    return Array.from(new Set(merged));
  };

  const orderedModelDefaults = useMemo(() => {
    const entries = Object.entries(modelDefaults);
    const order = [...ROLE_OPTIONS, ...entries.map(([role]) => role)];
    return entries.sort((a, b) => order.indexOf(a[0]) - order.indexOf(b[0]));
  }, [modelDefaults]);

  const orderedMemoryProfiles = useMemo(() => {
    const entries = Object.entries(memoryProfiles);
    const order = [...ROLE_OPTIONS, ...entries.map(([role]) => role)];
    return entries.sort((a, b) => order.indexOf(a[0]) - order.indexOf(b[0]));
  }, [memoryProfiles]);

  return (
    <section>
      <h2>Team Settings</h2>
      {error && <p style={{ color: "var(--danger)" }}>{error}</p>}
      <div className="card">
        <h3>Project Settings</h3>
        <div className="row">
          <label className="pill">Enable all tools for all agents</label>
          <input
            type="checkbox"
            checked={projectSettings?.allow_all_tools ?? false}
            onChange={(e) => updateProjectSettings({ allow_all_tools: e.target.checked })}
          />
        </div>
        <div className="muted" style={{ marginTop: 6 }}>
          High-risk tools still require approvals.
        </div>
        <div className="row" style={{ marginTop: 8 }}>
          <label className="pill">Allow high-risk without approval</label>
          <input
            type="checkbox"
            checked={projectSettings?.allow_high_risk ?? false}
            onChange={(e) => updateProjectSettings({ allow_high_risk: e.target.checked })}
          />
        </div>
        <div className="row" style={{ marginTop: 8 }}>
          <label className="pill">Default tool scopes</label>
          <input
            value={projectSettings?.default_tool_scopes ?? ""}
            onChange={(e) =>
              setProjectSettings((prev: ProjectSettings | null) =>
                prev ? { ...prev, default_tool_scopes: e.target.value } : prev
              )
            }
            onBlur={(e) => updateProjectSettings({ default_tool_scopes: e.target.value })}
            placeholder="system:run,mcp:call"
          />
        </div>
        <div className="row" style={{ marginTop: 8 }}>
          <label className="pill">Allow PM merge approval</label>
          <input
            type="checkbox"
            checked={projectSettings?.allow_pm_merge ?? false}
            onChange={(e) => updateProjectSettings({ allow_pm_merge: e.target.checked })}
          />
        </div>
        <div className="row" style={{ marginTop: 8 }}>
          <label className="pill">Auto-execute file edits</label>
          <input
            type="checkbox"
            checked={projectSettings?.auto_execute_edits ?? true}
            onChange={(e) => updateProjectSettings({ auto_execute_edits: e.target.checked })}
          />
        </div>
        <div className="row" style={{ marginTop: 8 }}>
          <label className="pill">Require PM approval before PR</label>
          <input
            type="checkbox"
            checked={projectSettings?.require_pm_pr_approval ?? true}
            onChange={(e) =>
              updateProjectSettings({ require_pm_pr_approval: e.target.checked })
            }
          />
        </div>
        <div className="row" style={{ marginTop: 8 }}>
          <label className="pill">Role tool scopes</label>
          <button
            className="secondary"
            onClick={() =>
              updateProjectSettings({ role_tool_scopes: JSON.stringify(roleToolScopes) })
            }
          >
            Save role scopes
          </button>
        </div>
        <div style={{ marginTop: 8 }}>
          {ROLE_OPTIONS.map((role: string) => (
            <div key={role} className="row" style={{ marginBottom: 6 }}>
              <span className="pill">{role}</span>
              <input
                value={roleToolScopes[role] ?? ""}
                onChange={(e) =>
                setRoleToolScopes((prev: Record<string, string>) => ({
                  ...prev,
                  [role]: e.target.value
                }))
                }
                placeholder="system:run,git:status"
              />
            </div>
          ))}
        </div>
        <div className="row" style={{ marginTop: 8 }}>
          <label className="pill">Chat target policy</label>
          <select
            value={projectSettings?.chat_target_policy ?? "managers"}
            onChange={(e) =>
              updateProjectSettings({ chat_target_policy: e.target.value })
            }
          >
            <option value="managers">Managers only</option>
            <option value="team">Full team</option>
          </select>
        </div>
        <div className="row" style={{ marginTop: 8 }}>
          <label className="pill">Task retry limit</label>
          <input
            type="number"
            min={1}
            value={projectSettings?.task_retry_limit ?? 3}
            onChange={(e) =>
              updateProjectSettings({ task_retry_limit: Number(e.target.value) })
            }
          />
        </div>
      </div>

      <div className="card">
        <h3>Goals</h3>
        <div className="row">
          <input
            value={goalTitle}
            onChange={(e) => setGoalTitle(e.target.value)}
            placeholder="Goal title"
          />
          <button onClick={createGoal}>Add Goal</button>
        </div>
        <ul style={{ marginTop: 8 }}>
          {goals.map((goal: GoalInfo) => (
            <li key={goal.id}>
              {goal.title}{" "}
              <select
                value={goal.status}
                onChange={(e) => updateGoalStatus(goal.id, e.target.value)}
              >
                <option value="open">Open</option>
                <option value="in_progress">In Progress</option>
                <option value="done">Done</option>
              </select>
            </li>
          ))}
        </ul>
      </div>

      <div className="card">
        <h3>Model Defaults by Role</h3>
        <label className="pill" style={{ marginBottom: 8 }}>
          <input
            type="checkbox"
            checked={showAllModels}
            onChange={(e) => setShowAllModels(e.target.checked)}
            style={{ marginRight: 6 }}
          />
          Show all models (slow)
        </label>
        {orderedModelDefaults.map(([role, entry]: [string, RoleModelDefault]) => (
          <div key={role} className="row" style={{ marginBottom: 6 }}>
            <span className="pill">{role}</span>
            <select
              value={entry.provider}
              onChange={(e) =>
                setModelDefaults((prev: Record<string, RoleModelDefault>) => ({
                  ...prev,
                  [role]: { ...entry, provider: e.target.value }
                }))
              }
            >
              {providersByKey.map((provider: string) => (
                <option key={provider} value={provider}>
                  {provider}
                </option>
              ))}
            </select>
            <select
              value={entry.model}
              onChange={(e) =>
                setModelDefaults((prev: Record<string, RoleModelDefault>) => ({
                  ...prev,
                  [role]: { ...entry, model: e.target.value }
                }))
              }
            >
              {modelOptionsFor(entry.provider, role, entry.model).map((modelId: string) => (
                <option key={modelId} value={modelId}>
                  {modelId}
                </option>
              ))}
            </select>
            <button
              className="danger"
              onClick={() =>
                setModelDefaults((prev: Record<string, RoleModelDefault>) => {
                  const next = { ...prev };
                  delete next[role];
                  return next;
                })
              }
            >
              Remove
            </button>
          </div>
        ))}
        <div className="row" style={{ marginTop: 8 }}>
          <input
            value={modelRoleName}
            onChange={(e) => setModelRoleName(e.target.value)}
            placeholder="Add role"
          />
          <button
            onClick={() => {
              const trimmed = modelRoleName.trim();
              if (!trimmed) {
                return;
              }
              const provider = providersByKey[0] || "";
              setModelDefaults((prev: Record<string, RoleModelDefault>) => ({
                ...prev,
                [trimmed]: { provider, model: "" }
              }));
              setModelRoleName("");
            }}
          >
            Add Role
          </button>
          <button
            className="secondary"
            onClick={() =>
              updateProjectSettings({ model_defaults: JSON.stringify(modelDefaults) })
            }
          >
            Save Defaults
          </button>
        </div>
      </div>

      <div className="card">
        <h3>Memory Profiles by Role</h3>
        {orderedMemoryProfiles.map(([role, profile]: [string, MemoryProfile]) => (
          <div key={role} className="row" style={{ marginBottom: 6 }}>
            <span className="pill">{role}</span>
            <input
              type="number"
              min={1}
              value={profile.cap}
              onChange={(e) =>
                setMemoryProfiles((prev: Record<string, MemoryProfile>) => ({
                  ...prev,
                  [role]: { ...profile, cap: Number(e.target.value) }
                }))
              }
            />
            <select
              value={profile.strategy}
              onChange={(e) =>
                setMemoryProfiles((prev: Record<string, MemoryProfile>) => ({
                  ...prev,
                  [role]: { ...profile, strategy: e.target.value }
                }))
              }
            >
              {MEMORY_STRATEGIES.map((strategy) => (
                <option key={strategy} value={strategy}>
                  {strategy}
                </option>
              ))}
            </select>
            <button
              className="danger"
              onClick={() =>
                setMemoryProfiles((prev: Record<string, MemoryProfile>) => {
                  const next = { ...prev };
                  delete next[role];
                  return next;
                })
              }
            >
              Remove
            </button>
          </div>
        ))}
        <div className="row" style={{ marginTop: 8 }}>
          <input
            value={memoryRoleName}
            onChange={(e) => setMemoryRoleName(e.target.value)}
            placeholder="Add role"
          />
          <button
            onClick={() => {
              const trimmed = memoryRoleName.trim();
              if (!trimmed) {
                return;
              }
              setMemoryProfiles((prev: Record<string, MemoryProfile>) => ({
                ...prev,
                [trimmed]: { cap: 5, strategy: "rolling" }
              }));
              setMemoryRoleName("");
            }}
          >
            Add Role
          </button>
          <button
            className="secondary"
            onClick={() =>
              updateProjectSettings({ memory_profiles: JSON.stringify(memoryProfiles) })
            }
          >
            Save Profiles
          </button>
        </div>
      </div>

      <div className="card">
        <h3>Memory Usage</h3>
        <ul>
          {agents.map((agent: AgentInfo) => (
            <li key={agent.id}>
              {agent.display_name ?? agent.role} ({agent.role}){" "}
              <span className="pill">
                {agent.id ? memoryCounts[agent.id] ?? 0 : 0} memories
              </span>
            </li>
          ))}
        </ul>
      </div>

      <div className="card">
        <h3>MCP Management</h3>
        <div className="row">
          <input
            value={mcpUrl}
            onChange={(e) => setMcpUrl(e.target.value)}
            placeholder="http://localhost:8765/mcp"
          />
          <button onClick={addMcpEndpoint}>Add Endpoint</button>
          <button className="secondary" onClick={refreshMcp}>
            Refresh Discovery
          </button>
        </div>
        <div className="row" style={{ marginTop: 8 }}>
          <input
            value={mcpPortsInput}
            onChange={(e) => setMcpPortsInput(e.target.value)}
            placeholder="Ports (comma-separated)"
          />
          <button className="secondary" onClick={updateMcpPorts}>
            Update Ports
          </button>
        </div>
        <div className="row" style={{ marginTop: 12 }}>
          <div style={{ flex: 1 }}>
            <h4>Manual Endpoints</h4>
            <ul>
              {mcpManual.map((url: string) => (
                <li key={url}>
                  {url}
                  <button className="danger" onClick={() => removeMcpEndpoint(url)}>
                    Remove
                  </button>
                </li>
              ))}
            </ul>
          </div>
          <div style={{ flex: 1 }}>
            <h4>Discovered</h4>
            <ul>
              {mcpDiscovered.map((endpoint: McpEndpointInfo) => (
                <li key={endpoint.url}>
                  {endpoint.url} <span className="pill">{endpoint.tools.length} tools</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>


      <div className="card">
        <h3>Plugins & Skills</h3>
        <ul>
          {plugins.map((plugin: PluginInfo) => (
            <li key={plugin.id}>
              <label className="pill">
                <input
                  type="checkbox"
                  checked={enabledPlugins.includes(plugin.id)}
                  onChange={(e) => {
                    const next = e.target.checked
                      ? [...enabledPlugins, plugin.id]
                      : enabledPlugins.filter((item: string) => item !== plugin.id);
                    setEnabledPlugins(next);
                    updateProjectSettings({ enabled_plugins: JSON.stringify(next) });
                  }}
                  style={{ marginRight: 6 }}
                />
                {plugin.name} ({plugin.id})
              </label>
            </li>
          ))}
        </ul>
      </div>

    </section>
  );
}
