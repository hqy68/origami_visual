"use client";

import { useEffect, useRef, useState } from "react";
import { CreasePattern, Legend, svgToFile } from "@/components/CreasePattern";
import { ModelGrid } from "@/components/ModelCard";
import { api, downloadJson, downloadText, slug, type GenerateResponse, type Health } from "@/lib/api";

type Mode = "text" | "photo";
const EXAMPLES = ["crane", "koi fish", "tulip", "fox", "paper airplane", "box"];
const MAX_BYTES = 5 * 1024 * 1024;

export default function Studio() {
  const [mode, setMode] = useState<Mode>("text");
  const [query, setQuery] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [hint, setHint] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<GenerateResponse | null>(null);
  const [health, setHealth] = useState<Health | null>(null);
  const svgRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    api.health().then(setHealth).catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    if (!file) return setPreview(null);
    const url = URL.createObjectURL(file);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  async function run(fn: () => Promise<GenerateResponse>) {
    setLoading(true);
    setError(null);
    try {
      setResult(await fn());
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  function submitText(q = query) {
    const text = q.trim();
    if (!text) return setError("Describe what you want to fold.");
    setQuery(text);
    run(() => api.generateText(text));
  }

  function submitPhoto() {
    if (!file) return setError("Choose a photo first.");
    if (file.size > MAX_BYTES) return setError("Image is larger than 5 MB; resize it and try again.");
    run(() => api.generatePhoto(file, hint.trim()));
  }

  const g = result?.generated;
  const name = g ? slug(g.subject) : "model";

  return (
    <div className="studio">
      <section className="intro">
        <h1>What do you want to fold?</h1>
        <p>
          Type an object or upload a photo. You get a crease pattern built from the best-matching traditional base,
          folding steps, and existing designs from the catalog.
        </p>
      </section>

      <section className="panel input-panel">
        <div className="tabs" role="tablist">
          <button role="tab" aria-selected={mode === "text"} onClick={() => setMode("text")}>
            Describe it
          </button>
          <button role="tab" aria-selected={mode === "photo"} onClick={() => setMode("photo")}>
            Upload a photo
          </button>
        </div>

        {mode === "text" ? (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              submitText();
            }}
          >
            <div className="row">
              <input
                type="text"
                value={query}
                maxLength={200}
                placeholder="e.g. a swan, a koi fish, a tulip"
                onChange={(e) => setQuery(e.target.value)}
                aria-label="Object to fold"
              />
              <button type="submit" className="primary" disabled={loading}>
                {loading ? "Working…" : "Generate"}
              </button>
            </div>
            <div className="chips">
              {EXAMPLES.map((ex) => (
                <button type="button" key={ex} className="chip" onClick={() => submitText(ex)} disabled={loading}>
                  {ex}
                </button>
              ))}
            </div>
          </form>
        ) : (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              submitPhoto();
            }}
          >
            <label className="dropzone">
              <input
                type="file"
                accept="image/jpeg,image/png,image/gif,image/webp"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              />
              {preview ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={preview} alt="Selected reference" />
              ) : (
                <span>Click to choose a JPEG, PNG, GIF or WebP (max 5 MB)</span>
              )}
            </label>
            <div className="row">
              <input
                type="text"
                value={hint}
                maxLength={200}
                placeholder="Optional hint, e.g. 'the bird on the left'"
                onChange={(e) => setHint(e.target.value)}
                aria-label="Hint about the photo"
              />
              <button type="submit" className="primary" disabled={loading || !file}>
                {loading ? "Analysing…" : "Generate"}
              </button>
            </div>
            {health && !health.vision && (
              <p className="note">
                Photo recognition needs an Anthropic API key on the backend (ANTHROPIC_API_KEY). Without it, add a
                hint and the hint is used instead.
              </p>
            )}
          </form>
        )}
        {health && <p className="fine">{health.catalog_count} models in the catalog.</p>}
      </section>

      {error && <div className="error" role="alert">{error}</div>}
      {result?.warning && <div className="note">{result.warning}</div>}

      {g && result && (
        <>
          <section className="panel result">
            <div className="result-head">
              <div>
                <p className="eyebrow">
                  {g.category} · body plan from {g.body_plan_source === "keywords" ? "keywords" : "Claude"}
                </p>
                <h2>{g.subject}</h2>
                <p>
                  Built on the <strong>{g.base.title.toLowerCase()}</strong> ({g.base.flaps}{" "}
                  {g.base.flaps === 1 ? "flap" : "flaps"}).
                </p>
              </div>
              <div className="actions">
                <button onClick={() => downloadJson(g.base.fold, `${name}.fold`)}>Download .fold</button>
                <button
                  onClick={() => svgRef.current && downloadText(svgToFile(svgRef.current), `${name}.svg`, "image/svg+xml")}
                >
                  Download .svg
                </button>
              </div>
            </div>

            <div className="result-body">
              <figure>
                <CreasePattern ref={svgRef} fold={g.base.fold} labels={g.flap_labels} title={`${g.subject} crease pattern`} />
                <Legend />
                <figcaption className={g.base.validation.flat_foldable_locally ? "ok" : "bad"}>
                  {g.base.validation.flat_foldable_locally
                    ? `✓ Locally flat-foldable (Kawasaki, Maekawa, big-little-big at ${g.base.validation.interior_vertices} interior vertices)`
                    : `✗ ${g.base.validation.failures.length} vertex check(s) failed`}
                </figcaption>
              </figure>

              <div className="steps">
                <h3>Fold the base</h3>
                <ol>
                  {g.steps.filter((s) => s.phase === "base").map((s, i) => <li key={i}>{s.text}</li>)}
                </ol>
                <h3>Shape the model</h3>
                <ol start={g.steps.filter((s) => s.phase === "base").length + 1}>
                  {g.steps.filter((s) => s.phase === "shaping").map((s, i) => <li key={i}>{s.text}</li>)}
                </ol>
                {g.notes.length > 0 && (
                  <div className="note">
                    {g.notes.map((n, i) => <p key={i}>{n}</p>)}
                  </div>
                )}
                <p className="fine">{g.disclaimer}</p>
              </div>
            </div>
          </section>

          <section>
            <h2>Existing designs</h2>
            {result.matches.length ? (
              <ModelGrid models={result.matches} />
            ) : (
              <p className="muted">No catalog matches for “{g.subject}” yet.</p>
            )}
          </section>
        </>
      )}
    </div>
  );
}
