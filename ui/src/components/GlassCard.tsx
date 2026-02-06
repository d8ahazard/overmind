import React from "react";

type Props = {
  title?: string;
  children: React.ReactNode;
};

export default function GlassCard({ title, children }: Props) {
  return (
    <section className="card">
      {title && <h3>{title}</h3>}
      {children}
    </section>
  );
}
