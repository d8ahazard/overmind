import { useEffect, useState } from "react";
import { apiDelete, apiGet, apiPost } from "../lib/api";
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

export default function Settings() {
  const [providers, setProviders] = useState([] as string[]);
  const [models, setModels] = useState([] as string[]);
  const [mcpStatus, setMcpStatus] = useState(null as MCPStatus | null);
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

  useEffect(() => {
    apiGet<string[]>("/models/providers")
      .then(setProviders)
      .catch((err) => setError(err.message));
    apiGet<{ id: string }[]>("/models")
      .then((data) => setModels(data.map((m) => m.id)))
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
    const updated = (await apiPost(`/agents/${editAgentId}`, editAgent)) as AgentConfig;
    setAgents((prev: AgentConfig[]) =>
      prev.map((agent: AgentConfig) => (agent.id === editAgentId ? updated : agent))
    );
    setEditAgentId(null);
    setEditAgent(null);
  };

  return (
    <section>
      <h2>Settings</h2>
      {error && <p style={{ color: "tomato" }}>{error}</p>}
      <h3>Providers</h3>
      <ul>
        {providers.map((provider: string) => (
          <li key={provider}>{provider}</li>
        ))}
      </ul>
      <h3>Models</h3>
      <ul>
        {models.map((model: string) => (
          <li key={model}>{model}</li>
        ))}
      </ul>
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
        <ul>
          {agents.map((agent: AgentConfig) => (
            <li key={agent.id}>
              {agent.display_name ?? agent.role} ({agent.role}) - {agent.provider}/{agent.model}
              <button
                className="secondary"
                style={{ marginLeft: 8 }}
                onClick={() => startEditAgent(agent)}
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
            <input
              value={editAgent.provider}
              onChange={(e) =>
                setEditAgent({ ...editAgent, provider: e.target.value })
              }
            />
            <input
              value={editAgent.model}
              onChange={(e) => setEditAgent({ ...editAgent, model: e.target.value })}
            />
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
