import type { SweepRequest, SweepResponse } from "./types";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export async function postSweep(
  request: SweepRequest,
  signal?: AbortSignal,
): Promise<SweepResponse> {
  const res = await fetch(`${API_URL}/sweep`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
    signal,
  });

  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`Sweep request failed (${res.status}): ${body}`);
  }

  return res.json() as Promise<SweepResponse>;
}
