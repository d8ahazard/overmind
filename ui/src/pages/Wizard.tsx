import { useEffect, useState } from "react";
import GlassCard from "../components/GlassCard";
import { apiGet, apiPost } from "../lib/api";

type ProviderKey = {
  provider: string;
  has_key: boolean;
};

type RecommendedDefaults = {
  manager?: string | null;
  worker?: string | null;
  code?: string | null;
  image?: string | null;
};

type RecommendedEntry = {
  defaults?: RecommendedDefaults;
};

export default function Wizard() {
  const [step, setStep] = useState(1);
  const [keys, setKeys] = useState([] as ProviderKey[]);
  const [models, setModels] = useState([] as { id: string; provider: string }[]);
  const [recommended, setRecommended] = useState({} as Record<string, RecommendedEntry>);
  const [provider, setProvider] = useState("openai");
  const [value, setValue] = useState("");

  useEffect(() => {
    apiGet("/keys")
      .then((data) => setKeys(data as ProviderKey[]))
      .catch(() => setKeys([]));
    apiGet("/models?only_enabled=true")
      .then((data) => setModels(data as { id: string; provider: string }[]))
      .catch(() => setModels([]));
    apiGet("/models/recommended?only_enabled=true")
      .then((data) => setRecommended(data as Record<string, any>))
      .catch(() => setRecommended({}));
  }, []);

  const saveKey = async () => {
    await apiPost("/keys", { provider, key: value });
    setValue("");
    const data = (await apiGet("/keys")) as ProviderKey[];
    setKeys(data);
    const modelData = (await apiGet("/models?only_enabled=true")) as {
      id: string;
      provider: string;
    }[];
    setModels(modelData);
    const rec = (await apiGet("/models/recommended?only_enabled=true")) as Record<string, any>;
    setRecommended(rec);
    setStep(2);
  };

  const hasAnyKey = keys.some((item: ProviderKey) => item.has_key);

  return (
    <section>
      <h2>Setup Wizard</h2>
      <GlassCard title={`Step ${step}: API Keys`}>
        <div className="row">
          <input value={provider} onChange={(e) => setProvider(e.target.value)} />
          <input value={value} onChange={(e) => setValue(e.target.value)} placeholder="API key" />
          <button onClick={saveKey}>Save</button>
        </div>
        <div className="muted">At least one key is required to proceed.</div>
      </GlassCard>
      <GlassCard title="Step 2: Agent Configuration">
        {hasAnyKey ? (
          <div>
            <div className="muted">
              Keys detected. Recommended defaults are pre-selected for each role.
            </div>
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
          </div>
        ) : (
          <div className="muted">No keys detected. Add a key to continue.</div>
        )}
      </GlassCard>
    </section>
  );
}
