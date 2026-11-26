"use client";

import { useEffect, useState } from "react";
import { CreasePattern, Legend } from "@/components/CreasePattern";
import { api, downloadJson, type Base } from "@/lib/api";

export default function Bases() {
  const [bases, setBases] = useState<Base[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.bases().then((r) => setBases(r.bases)).catch((e) => setError(e.message));
  }, []);

  return (
    <div>
      <h1>Traditional bases</h1>
      <p className="muted">Most origami models start from one of these. Every crease pattern here is computed and checked for local flat-foldability.</p>
      <Legend />
      {error && <div className="error" role="alert">{error}</div>}
      {!bases && !error && <p className="muted">Loading…</p>}
      <div className="base-grid">
        {bases?.map((b) => (
          <article key={b.id} className="panel base-card">
            <CreasePattern fold={b.fold} />
            <div>
              <h2>{b.title}</h2>
              <p className="muted">{b.description} {b.flaps} {b.flaps === 1 ? "flap" : "flaps"}.</p>
              <details>
                <summary>Steps</summary>
                <ol>{b.steps.map((s, i) => <li key={i}>{s}</li>)}</ol>
              </details>
              <p className={b.validation.flat_foldable_locally ? "ok fine" : "bad fine"}>
                {b.validation.flat_foldable_locally ? "✓ Locally flat-foldable" : "✗ Fails flat-foldability checks"}
              </p>
              <button onClick={() => downloadJson(b.fold, `${b.id}-base.fold`)}>Download .fold</button>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}
