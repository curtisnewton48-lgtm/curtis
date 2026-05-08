import modelConfig from "../config/models.json";

type JsonSchema = Record<string, unknown>;
type GeminiCaller = (purpose: string, prompt: string, schema: JsonSchema) => Promise<unknown>;

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
): Promise<unknown> {
  if (testCaller) {
    return testCaller(purpose, prompt, schema);
  }

  const apiKey = process.env.GEMINI_API_KEY;
  if (!apiKey) {
    throw new Error("GEMINI_API_KEY is required.");
  }

  const configuredModels = modelConfig as Record<string, string>;
  const model = process.env.STAGE_TWO_MODEL_NAME || configuredModels[purpose] || "gemini-3.1-pro";

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
                text: `${prompt}\n\nReturn JSON only matching this schema:\n${JSON.stringify(schema)}`,
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
  return JSON.parse(text);
}
