import { useEffect, useState } from "react";
import { apiDelete, apiGet, apiPost, apiPut } from "../lib/api";
import Notifications from "../components/Notifications";

type MCPStatus = {
  last_refresh: string | null;
  endpoints: { url: string; tools: { name: string }[] }[];
};

type PersonalityTemplate = {
  id?: number;
  role: string;
  name: string;
  script: string;
};

type ProviderKey = {
  id?: number;
  provider: string;
  has_key: boolean;
};

type AgentConfig = {
  id?: number;
  display_name?: string | null;
  role: string;
  personality?: string | null;
  provider: string;
  model: string;
};

type ModelInfo = {
  id: string;
  provider: string;
  supports_tools?: boolean;
  supports_vision?: boolean;
  context_length?: number;
  recommended_roles?: string[] | null;
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

type ProjectSettings = {
  project_id: number;
  allow_all_tools: boolean;
  allow_high_risk: boolean;
  default_tool_scopes?: string | null;
};

export default function Settings() {
  const [providers, setProviders] = useState([] as string[]);
  const [models, setModels] = useState([] as ModelInfo[]);
  const [providersByKey, setProvidersByKey] = useState([] as string[]);
  const [mcpStatus, setMcpStatus] = useState(null as MCPStatus | null);
  const [recommended, setRecommended] = useState({} as Record<string, RecommendedEntry>);
  const [showAllModels, setShowAllModels] = useState(false);
  const [error, setError] = useState(null as string | null);
  const [templates, setTemplates] = useState([] as PersonalityTemplate[]);
  const [templateRole, setTemplateRole] = useState("Developer");
  const [templateName, setTemplateName] = useState("Default");
  const [templateScript, setTemplateScript] = useState(
    "Practical, curious, and focused on clean, working code."
  );
  const [providerKeys, setProviderKeys] = useState([] as ProviderKey[]);
  const [providerName, setProviderName] = useState("openai");
  const [providerValue, setProviderValue] = useState("");
  const [availableProviders, setAvailableProviders] = useState([] as { id: string; name: string }[]);
  const [plugins, setPlugins] = useState([] as { id: string; name: string }[]);
  const [agents, setAgents] = useState([] as AgentConfig[]);
  const [editAgentId, setEditAgentId] = useState(null as number | null);
  const [editAgent, setEditAgent] = useState(null as AgentConfig | null);
  const [projectSettings, setProjectSettings] = useState(null as ProjectSettings | null);

  const toProviderLabel = (value: unknown) => {
    if (typeof value === "string") {
      return value;
    }
    if (value && typeof value === "object") {
      const maybe = value as { provider?: string; id?: string };
      return maybe.provider ?? maybe.id ?? "";
    }
    return "";
  };

  const toModelId = (value: unknown) => {
    if (typeof value === "string") {
      return value;
    }
    if (value && typeof value === "object") {
      const maybe = value as { id?: string; model?: string; name?: string };
      return maybe.id ?? maybe.model ?? maybe.name ?? "";
    }
    return "";
  };

  const toModelLabel = (value: unknown) => {
    const id = toModelId(value);
    return id || "unknown";
  };

  useEffect(() => {
    apiGet<unknown[]>("/models/providers")
      .then((data) =>
        setProviders(
          (data as unknown[]).map((item) =>
            toProviderLabel(item)
          ).filter(Boolean)
        )
      )
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
    apiGet<MCPStatus>("/mcp/status")
      .then(setMcpStatus)
      .catch((err) => setError(err.message));
    apiGet("/personalities")
      .then((data) => setTemplates(data as PersonalityTemplate[]))
      .catch((err) => setError(err.message));
    apiGet("/keys")
      .then((data) => setProviderKeys(data as ProviderKey[]))
      .catch((err) => setError(err.message));
    apiGet("/agents")
      .then((data) => setAgents(data as AgentConfig[]))
      .catch((err) => setError(err.message));
    apiGet("/projects/settings")
      .then((data) => setProjectSettings(data as ProjectSettings))
      .catch((err) => setError(err.message));
    apiGet("/providers")
      .then((data) => setAvailableProviders(data as { id: string; name: string }[]))
      .catch((err) => setError(err.message));
    apiGet("/providers/plugins")
      .then((data) => setPlugins(data as { id: string; name: string }[]))
      .catch((err) => setError(err.message));
  }, []);

  const refreshMcp = async () => {
    setError(null);
    try {
      await apiPost("/mcp/refresh", {});
      const status = await apiGet<MCPStatus>("/mcp/status");
      setMcpStatus(status);
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

  const startEditAgent = (agent: AgentConfig) => {
    setEditAgentId(agent.id ?? null);
    setEditAgent({ ...agent });
  };

  const saveAgent = async () => {
    if (!editAgentId || !editAgent) {
      return;
    }
    const updated = (await apiPut(`/agents/${editAgentId}`, editAgent)) as AgentConfig;
    setAgents((prev: AgentConfig[]) =>
      prev.map((agent: AgentConfig) => (agent.id === editAgentId ? updated : agent))
    );
    setEditAgentId(null);
    setEditAgent(null);
  };

  const modelsForProvider = (providerName: string) =>
    models
      .filter((item: ModelInfo) => item.provider === providerName)
      .map((item: ModelInfo) => item.id);

  const getRecommendedModels = (providerName: string, roleName: string) => {
    const entry = recommended?.[providerName];
    const available = entry?.models ?? {};
    const roleLower = roleName.toLowerCase();
    if (roleLower.includes("developer") || roleLower.includes("engineer") || roleLower.includes("tech")) {
      const picked = available.code?.length ? available.code : available.text ?? [];
      return picked.map(toModelId).filter(Boolean);
    }
    if (roleLower.includes("designer") || roleLower.includes("artist")) {
      const picked = available.image?.length ? available.image : available.text ?? [];
      return picked.map(toModelId).filter(Boolean);
    }
    return (available.text ?? []).map(toModelId).filter(Boolean);
  };

  const modelOptionsFor = (providerName: string, roleName: string, currentValue: string) => {
    const base = showAllModels
      ? modelsForProvider(providerName)
      : getRecommendedModels(providerName, roleName);
    const merged = [...base, toModelId(currentValue)].filter(Boolean);
    return Array.from(new Set(merged));
  };

  const updateProjectSetting = async (allowAllTools: boolean) => {
    setError(null);
    try {
      const updated = (await apiPut("/projects/settings", {
        allow_all_tools: allowAllTools
      })) as ProjectSettings;
      setProjectSettings(updated);
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

  return (
    <section>
      <h2>Settings</h2>
      {error && <p style={{ color: "tomato" }}>{error}</p>}
      <h3>Providers</h3>
      <ul>
        {providers.map((provider: string, index: number) => {
          const label = toProviderLabel(provider);
          return <li key={`${label}-${index}`}>{label}</li>;
        })}
      </ul>
      <h3>Model Defaults</h3>
      <div className="card">
        {Object.keys(recommended).length === 0 && (
          <div className="muted">No recommended models available yet.</div>
        )}
        {(Object.entries(recommended) as [string, RecommendedEntry][])
          .map(([providerName, info]) => (
            <div key={providerName} style={{ marginBottom: 10 }}>
              <strong>{providerName}</strong>
              <div className="row">
                <span className="pill">Manager: {info.defaults?.manager ?? "n/a"}</span>
                <span className="pill">Worker: {info.defaults?.worker ?? "n/a"}</span>
                <span className="pill">Code: {info.defaults?.code ?? "n/a"}</span>
                <span className="pill">Image: {info.defaults?.image ?? "n/a"}</span>
              </div>
            </div>
          ))}
      </div>
      <h3>Notifications</h3>
      <Notifications events={[]} />
      <h3>Unity MCP</h3>
      <button onClick={refreshMcp} style={{ marginBottom: 8 }}>
        Refresh MCP Discovery
      </button>
      {mcpStatus ? (
        <div>
          <div style={{ fontSize: 12, color: "#666" }}>
            Last refresh: {mcpStatus.last_refresh ?? "never"}
          </div>
          <ul>
            {mcpStatus.endpoints.map((endpoint: { url: string; tools: { name: string }[] }) => (
              <li key={endpoint.url}>
                {endpoint.url} ({endpoint.tools.length} tools)
              </li>
            ))}
          </ul>
        </div>
      ) : (
        <p>No MCP endpoints discovered yet.</p>
      )}
      <p style={{ color: "#666" }}>
        Configure provider keys via environment variables on the backend.
      </p>
      <h3>Provider Keys</h3>
      <div className="card">
        <div className="row">
          <select value={providerName} onChange={(e) => setProviderName(e.target.value)}>
            {availableProviders.map((provider: { id: string; name: string }) => (
              <option key={provider.id} value={provider.id}>
                {provider.name}
              </option>
            ))}
          </select>
          <input
            value={providerValue}
            onChange={(e) => setProviderValue(e.target.value)}
            placeholder="API key"
          />
          <button onClick={upsertKey}>Save Key</button>
        </div>
      </div>
      <div className="card">
        <h3>Provider Catalog</h3>
        <ul>
          {availableProviders.map((provider: { id: string; name: string }) => (
            <li key={provider.id}>
              {provider.name} <span className="pill">{provider.id}</span>
            </li>
          ))}
        </ul>
        <h3>Plugins & Skills</h3>
        <ul>
          {plugins.map((plugin: { id: string; name: string }) => (
            <li key={plugin.id}>
              {plugin.name} <span className="pill">{plugin.id}</span>
            </li>
          ))}
        </ul>
      </div>
      <h3>Project Settings</h3>
      <div className="card">
        <div className="row">
          <label className="pill">Enable all tools for all agents</label>
          <input
            type="checkbox"
            checked={projectSettings?.allow_all_tools ?? false}
            onChange={(e) => updateProjectSetting(e.target.checked)}
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
      </div>
      <div className="card">
        <ul>
          {agents.map((agent: AgentConfig) => (
            <li key={agent.id}>
              {agent.display_name ?? agent.role} ({agent.role}) - {agent.provider}/
              {toModelLabel(agent.model)}
              <button
                className="secondary"
                style={{ marginLeft: 8 }}
                onClick={() =>
                  startEditAgent({
                    ...agent,
                    model: toModelId(agent.model)
                  })
                }
              >
                Edit
              </button>
            </li>
          ))}
        </ul>
      </div>
      {editAgent && (
        <div className="card">
          <h3>Edit Agent</h3>
          <label className="pill" style={{ marginBottom: 8 }}>
            <input
              type="checkbox"
              checked={showAllModels}
              onChange={(e) => setShowAllModels(e.target.checked)}
              style={{ marginRight: 6 }}
            />
            Show all models (slow)
          </label>
          <div className="row">
            <input
              value={editAgent.display_name ?? ""}
              onChange={(e) =>
                setEditAgent({ ...editAgent, display_name: e.target.value })
              }
            />
            <input
              value={editAgent.role}
              onChange={(e) => setEditAgent({ ...editAgent, role: e.target.value })}
            />
            <input
              value={editAgent.personality ?? ""}
              onChange={(e) =>
                setEditAgent({ ...editAgent, personality: e.target.value })
              }
            />
            <select
              value={editAgent.provider}
              onChange={(e) =>
                setEditAgent({ ...editAgent, provider: e.target.value })
              }
            >
              {providersByKey.map((providerName: string) => (
                <option key={providerName} value={providerName}>
                  {providerName}
                </option>
              ))}
            </select>
            <select
              value={toModelId(editAgent.model)}
              onChange={(e) => setEditAgent({ ...editAgent, model: e.target.value })}
            >
              {modelOptionsFor(editAgent.provider, editAgent.role, editAgent.model).map(
                (modelId: string) => (
                <option key={modelId} value={modelId}>
                  {modelId}
                </option>
              )
              )}
            </select>
            <button onClick={saveAgent}>Save</button>
          </div>
        </div>
      )}
      <div className="card">
        <ul>
          {providerKeys.map((item: ProviderKey) => (
            <li key={item.provider}>
              {item.provider}{" "}
              <span className="pill">{item.has_key ? "configured" : "missing"}</span>
              <button
                className="danger"
                style={{ marginLeft: 8 }}
                onClick={() => deleteKey(item.provider)}
              >
                Delete
              </button>
            </li>
          ))}
        </ul>
        <div className="muted">
          Models are filtered to providers with configured keys.
        </div>
      </div>
      <h3>Memory Model</h3>
      <p style={{ color: "#666" }}>
        Each agent keeps a rolling memory log. We store the last few actions per agent
        and surface them in prompts to preserve context. The Memory Feed in Run Console
        shows updates in real time.
      </p>
      <h3>Personality Templates</h3>
      <div className="card">
        <div className="row">
          <input
            value={templateRole}
            onChange={(e) => setTemplateRole(e.target.value)}
            placeholder="Role"
          />
          <input
            value={templateName}
            onChange={(e) => setTemplateName(e.target.value)}
            placeholder="Template name"
          />
          <input
            value={templateScript}
            onChange={(e) => setTemplateScript(e.target.value)}
            placeholder="Personality script"
          />
          <button onClick={createTemplate}>Add Template</button>
        </div>
      </div>
      <div className="card">
        <ul>
          {templates.map((template: PersonalityTemplate) => (
            <li key={template.id}>
              {template.role} - {template.name}
              <div className="muted">{template.script}</div>
              {template.id && (
                <button
                  className="danger"
                  onClick={() => deleteTemplate(template.id as number)}
                  style={{ marginTop: 6 }}
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
