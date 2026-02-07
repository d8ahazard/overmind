import { useEffect, useState } from "react";
import { apiDelete, apiGet, apiPost } from "../lib/api";

type ProviderKey = {
  id?: number;
  provider: string;
  has_key: boolean;
};

type PersonalityTemplate = {
  id?: number;
  role: string;
  name: string;
  script: string;
};

export default function Settings() {
  const [error, setError] = useState(null as string | null);
  const [providerKeys, setProviderKeys] = useState([] as ProviderKey[]);
  const [providerName, setProviderName] = useState("openai");
  const [providerValue, setProviderValue] = useState("");
  const [availableProviders, setAvailableProviders] = useState([] as { id: string; name: string }[]);
  const [templates, setTemplates] = useState([] as PersonalityTemplate[]);
  const [templateRole, setTemplateRole] = useState("Developer");
  const [templateName, setTemplateName] = useState("Default");
  const [templateScript, setTemplateScript] = useState(
    "Be concise, collaborative, and focus on shipping high-quality work."
  );

  useEffect(() => {
    apiGet("/keys")
      .then((data) => setProviderKeys(data as ProviderKey[]))
      .catch((err) => setError((err as Error).message));
    apiGet("/providers")
      .then((data) => setAvailableProviders(data as { id: string; name: string }[]))
      .catch((err) => setError((err as Error).message));
    apiGet("/personalities")
      .then((data) => setTemplates(data as PersonalityTemplate[]))
      .catch((err) => setError((err as Error).message));
  }, []);

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

  return (
    <section>
      <h2>Settings</h2>
      {error && <p style={{ color: "var(--danger)" }}>{error}</p>}
      <div className="card">
        <h3>Provider Keys</h3>
        <div className="row">
          <select value={providerName} onChange={(e) => setProviderName(e.target.value)}>
            {availableProviders.map((provider) => (
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
        <ul style={{ marginTop: 8 }}>
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
      </div>

      <div className="card">
        <h3>Default Profiles</h3>
        <div className="row">
          <input value={templateRole} onChange={(e) => setTemplateRole(e.target.value)} />
          <input value={templateName} onChange={(e) => setTemplateName(e.target.value)} />
          <input value={templateScript} onChange={(e) => setTemplateScript(e.target.value)} />
          <button onClick={createTemplate}>Save</button>
        </div>
        <ul>
          {templates.map((template) => (
            <li key={template.id}>
              {template.role}: {template.name}
              <button
                className="danger"
                style={{ marginLeft: 8 }}
                onClick={() => template.id && deleteTemplate(template.id)}
              >
                Delete
              </button>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
