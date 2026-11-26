/* eslint-disable @next/next/no-img-element -- thumbnails are hotlinked from the source site */
import type { CatalogModel } from "@/lib/api";

export function ModelCard({ model }: { model: CatalogModel }) {
  return (
    <a className="model-card" href={model.url} target="_blank" rel="noopener noreferrer">
      <div className="thumb">
        {model.image_url ? (
          <img src={model.image_url} alt="" loading="lazy" referrerPolicy="no-referrer" />
        ) : (
          <span className="thumb-empty">{model.kind === "crease_pattern" ? "CP" : "No image"}</span>
        )}
      </div>
      <div className="model-body">
        <h3>{model.title}</h3>
        <p className="meta">
          {model.designer ?? "Unknown designer"}
          {model.difficulty ? ` · ${model.difficulty}` : ""}
        </p>
        <p className="meta">
          <span className={`kind ${model.kind}`}>{model.kind === "crease_pattern" ? "Crease pattern" : "Tutorial"}</span>
          {" "}on {model.source} ↗
        </p>
      </div>
    </a>
  );
}

export function ModelGrid({ models }: { models: CatalogModel[] }) {
  return (
    <>
      <div className="model-grid">
        {models.map((m) => (
          <ModelCard key={m.id} model={m} />
        ))}
      </div>
      <p className="fine">
        Images and instructions belong to their source sites and designers; cards link to the original page.
      </p>
    </>
  );
}
