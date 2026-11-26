"use client";

import { useState } from "react";
import { ModelGrid } from "@/components/ModelCard";
import { api, type CatalogModel } from "@/lib/api";

const SUGGESTIONS = ["dragon", "insect", "flower", "box", "fish", "star"];

export default function Catalog() {
  const [q, setQ] = useState("");
  const [results, setResults] = useState<CatalogModel[] | null>(null);
  const [searched, setSearched] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function go(term = q) {
    const t = term.trim();
    if (!t) return;
    setQ(t);
    setLoading(true);
    setError(null);
    try {
      const r = await api.search(t);
      setResults(r.results);
      setSearched(t);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <h1>Catalog</h1>
      <p className="muted">Search tutorials and crease patterns collected from origami sites.</p>
      <form
        className="row"
        onSubmit={(e) => {
          e.preventDefault();
          go();
        }}
      >
        <input type="search" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search models" aria-label="Search models" />
        <button type="submit" className="primary" disabled={loading}>
          {loading ? "Searching…" : "Search"}
        </button>
      </form>
      <div className="chips">
        {SUGGESTIONS.map((s) => (
          <button key={s} className="chip" onClick={() => go(s)}>{s}</button>
        ))}
      </div>
      {error && <div className="error" role="alert">{error}</div>}
      {results &&
        (results.length ? (
          <ModelGrid models={results} />
        ) : (
          <p className="muted">No models match “{searched}”.</p>
        ))}
    </div>
  );
}
