import { createServerFn } from "@tanstack/react-start";

export type SweepSuggestion = {
  preset: "soup" | "garden" | "gliders" | "rpen" | "acorn" | "pulsar" | "gun";
  fieldStrength: number;
  similarityThreshold: number;
  coupling: number;
  innate: boolean;
  cells: number;
  density: number;
  note: string;
};

const PRESETS = ["soup", "garden", "gliders", "rpen", "acorn", "pulsar", "gun"] as const;

function clamp(n: number, lo: number, hi: number) {
  return Math.max(lo, Math.min(hi, n));
}

function parseSuggestion(text: string): SweepSuggestion | null {
  const start = text.indexOf("{");
  const end = text.lastIndexOf("}");
  if (start < 0 || end <= start) return null;
  try {
    const raw = JSON.parse(text.slice(start, end + 1)) as Record<string, unknown>;
    const preset = PRESETS.includes(raw.preset as (typeof PRESETS)[number])
      ? (raw.preset as SweepSuggestion["preset"])
      : "garden";
    const cells = Math.round(clamp(Number(raw.cells) || 32, 16, 64) / 2) * 2;
    return {
      preset,
      fieldStrength: clamp(Number(raw.fieldStrength) || 0.8, 0, 1),
      similarityThreshold: clamp(Number(raw.similarityThreshold) || 0.55, 0.4, 0.92),
      coupling: clamp(Number(raw.coupling) || 0, 0, 1),
      innate: raw.innate !== false,
      cells,
      density: clamp(Number(raw.density) || 0.25, 0.05, 0.55),
      note: typeof raw.note === "string" ? raw.note.slice(0, 240) : "Grok picked the next freeze.",
    };
  } catch {
    return null;
  }
}

export const suggestNextSweep = createServerFn({ method: "POST" })
  .validator((input: { journal: string }) => {
    if (!input || typeof input.journal !== "string") throw new Error("Missing the campaign journal.");
    return { journal: input.journal.slice(0, 3500) };
  })
  .handler(async ({ data }) => {
    const apiKey = process.env.XAI_API_KEY;
    if (!apiKey) return { ok: false as const, error: "Grok is not available. Autopilot will choose the next sweep itself." };
    try {
      const res = await fetch("https://api.x.ai/v1/chat/completions", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${apiKey}`,
        },
        body: JSON.stringify({
          model: "grok-4.5",
          max_tokens: 280,
          temperature: 0.3,
          messages: [
            {
              role: "system",
              content:
                "You choose the next frozen configuration for a four-board Conway test. Control is never modified. Field may overwrite from a crystal table. Yoked writes the same number of flips at random. Scrambled permutes the crystals. Specific means field facilitation beats both nulls. That is still not morphic resonance. Prefer isolated patterns (garden, gliders, rpen), coupling 0, and a similarity that arms the field (about 1–12% flips) without going loud. Return JSON only: {\"preset\":\"garden\",\"fieldStrength\":0.8,\"similarityThreshold\":0.55,\"coupling\":0,\"innate\":true,\"cells\":32,\"density\":0.25,\"note\":\"one sentence\"}.",
            },
            { role: "user", content: data.journal },
          ],
        }),
      });
      if (!res.ok) return { ok: false as const, error: `Grok could not answer (${res.status}). The local playbook continues.` };
      const body = (await res.json()) as { choices?: { message?: { content?: string } }[] };
      const text = body.choices?.[0]?.message?.content ?? "";
      const plan = parseSuggestion(text);
      if (!plan) return { ok: false as const, error: "Grok's reply was not a usable recipe. The local playbook continues." };
      return { ok: true as const, plan };
    } catch {
      return { ok: false as const, error: "Grok could not be reached. The local playbook continues." };
    }
  });
