import { useEffect, useState } from "react";

type NotificationEvent = {
  title: string;
  body: string;
};

export default function Notifications({ events }: { events: NotificationEvent[] }) {
  const [enabled, setEnabled] = useState(false);

  useEffect(() => {
    if (Notification.permission === "granted") {
      setEnabled(true);
    }
  }, []);

  useEffect(() => {
    if (!enabled) {
      return;
    }
    const latest = events[events.length - 1];
    if (latest) {
      new Notification(latest.title, { body: latest.body });
    }
  }, [events, enabled]);

  const requestPermission = async () => {
    const permission = await Notification.requestPermission();
    setEnabled(permission === "granted");
  };

  return (
    <div className="card">
      <h3>Notifications</h3>
      <div className="row">
        <button onClick={requestPermission} className="secondary">
          {enabled ? "Enabled" : "Enable Notifications"}
        </button>
        <span className="muted">
          Browser alerts fire when stakeholder feedback is routed to managers.
        </span>
      </div>
    </div>
  );
}
