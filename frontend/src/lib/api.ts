// Types mirror the FastAPI responses in backend/app/main.py.

export type Assignment = "M" | "V" | "B" | "F" | "U";

export interface FoldFile {
  frame_title?: string;
  vertices_coords: [number, number][];
  edges_vertices: [number, number][];
  edges_assignment: Assignment[];
  [key: string]: unknown;
}

export interface Validation {
  flat_foldable_locally: boolean;
  interior_vertices: number;
  checks: string[];
  failures: { vertex: number; coords: [number, number]; kawasaki: boolean; maekawa: boolean; big_little_big: boolean }[];
}

export interface Base {
  id: string;
  title: string;
  description: string;
  fold: FoldFile;
  validation: Validation;
  steps: string[];
  flaps: number;
}

export interface CatalogModel {
  id: number;
  source: string;
  url: string;
  title: string;
  designer: string | null;
  kind: "crease_pattern" | "tutorial";
  difficulty: string | null;
  description: string | null;
  image_url: string | null;
  tags: string[];
  license_note: string | null;
  score?: number;
}

export interface BodyPlan {
  subject: string;
  category: string;
  appendages: string[];
  search_terms: string[];
  notes: string | null;
  source: string;
}

export interface Generated {
  subject: string;
  category: string;
  body_plan_source: string;
  base: Base;
  flap_labels: { corner: [number, number]; part: string }[];
  steps: { phase: "base" | "shaping"; text: string }[];
  notes: string[];
  disclaimer: string;
}

export interface GenerateResponse {
  plan: BodyPlan;
  generated: Generated;
  matches: CatalogModel[];
  warning: string | null;
}

export interface Health {
  ok: boolean;
  catalog_count: number;
  vision: boolean;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(path, init);
  } catch {
    throw new Error("Can't reach the API. Is the backend running on port 8000?");
  }
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const body = await res.json();
      if (typeof body.detail === "string") detail = body.detail;
      else if (Array.isArray(body.detail)) detail = body.detail.map((d: { msg: string }) => d.msg).join("; ");
    } catch {
      if (res.status >= 500) detail = "The API is not responding. Is the backend running on port 8000?";
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => request<Health>("/api/health"),
  search: (q: string, limit = 24) =>
    request<{ query: string; results: CatalogModel[] }>(`/api/search?q=${encodeURIComponent(q)}&limit=${limit}`),
  generateText: (query: string) =>
    request<GenerateResponse>("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query }),
    }),
  generatePhoto: (file: File, hint: string) => {
    const form = new FormData();
    form.append("file", file);
    form.append("hint", hint);
    return request<GenerateResponse>("/api/generate/photo", { method: "POST", body: form });
  },
  bases: () => request<{ bases: Base[] }>("/api/bases"),
};

export function downloadJson(data: unknown, filename: string) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
  triggerDownload(blob, filename);
}

export function downloadText(text: string, filename: string, type: string) {
  triggerDownload(new Blob([text], { type }), filename);
}

function triggerDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export function slug(s: string) {
  return s.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") || "model";
}
