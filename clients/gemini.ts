import modelConfig from "../config/models.json";

type JsonSchema = Record<string, unknown>;
type GeminiCaller = (purpose: string, prompt: string, schema: JsonSchema) => Promise<unknown>;
type GeminiOptions = {
  arrayMode?: boolean;
};

declare const process: {
  env: Record<string, string | undefined>;
};

let testCaller: GeminiCaller | null = null;

export function setGeminiCallerForTest(caller: GeminiCaller | null): void {
  testCaller = caller;
}

export async function callGemini(
  purpose: string,
  prompt: string,
  schema: JsonSchema,
  options: GeminiOptions = {},
): Promise<unknown> {
  if (testCaller) {
    return testCaller(purpose, prompt, schema);
  }

  const apiKey = process.env.GEMINI_API_KEY;
  if (!apiKey) {
    throw new Error("GEMINI_API_KEY is required.");
  }

  const configuredModels = modelConfig as Record<string, string>;
  const model =
    purpose === "stage1"
      ? process.env.STAGE_ONE_MODEL_NAME || configuredModels[purpose] || "gemini-3.0-flash"
      : process.env.STAGE_TWO_MODEL_NAME || configuredModels[purpose] || "gemini-3.1-pro";
  const responseContract = options.arrayMode
    ? `Return JSON only as an array. Each item must match this schema:\n${JSON.stringify(schema)}`
    : `Return JSON only matching this schema:\n${JSON.stringify(schema)}`;

  const response = await fetch(
    `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${apiKey}`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        contents: [
          {
            role: "user",
            parts: [
              {
                text: `${prompt}\n\n${responseContract}`,
              },
            ],
          },
        ],
        generationConfig: {
          responseMimeType: "application/json",
        },
      }),
    },
  );

  if (!response.ok) {
    throw new Error(`Gemini ${purpose} call failed: ${response.status} ${await response.text()}`);
  }

  const payload = await response.json();
  const text = payload?.candidates?.[0]?.content?.parts?.[0]?.text;
  if (typeof text !== "string") {
    return text;
  }
  const parsed = JSON.parse(text);
  if (options.arrayMode && !Array.isArray(parsed)) {
    if (Array.isArray(parsed?.items)) return parsed.items;
    if (Array.isArray(parsed?.jobs)) return parsed.jobs;
    throw new Error(`Gemini ${purpose} response was not an array.`);
  }
  return parsed;
}
