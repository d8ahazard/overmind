import { useEffect, useState } from "react";
import GlassCard from "../components/GlassCard";
import { apiGet, apiPost } from "../lib/api";

type ProviderKey = {
  provider: string;
  has_key: boolean;
};

export default function Wizard() {
  const [step, setStep] = useState(1);
  const [keys, setKeys] = useState([] as ProviderKey[]);
  const [models, setModels] = useState([] as { id: string; provider: string }[]);
  const [provider, setProvider] = useState("openai");
  const [value, setValue] = useState("");

  useEffect(() => {
    apiGet("/keys")
      .then((data) => setKeys(data as ProviderKey[]))
      .catch(() => setKeys([]));
    apiGet("/models?only_enabled=true")
      .then((data) => setModels(data as { id: string; provider: string }[]))
      .catch(() => setModels([]));
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
    setStep(2);
  };

  const hasAnyKey = keys.some((item) => item.has_key);

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
            <div className="muted">Keys detected. Select a model and continue.</div>
            <ul>
              {models.map((model) => (
                <li key={model.id}>
                  {model.id} <span className="pill">{model.provider}</span>
                </li>
              ))}
            </ul>
          </div>
        ) : (
          <div className="muted">No keys detected. Add a key to continue.</div>
        )}
      </GlassCard>
    </section>
  );
}
