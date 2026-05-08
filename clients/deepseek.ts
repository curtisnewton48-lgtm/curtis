import modelConfig from "../config/models.json";

type JsonSchema = Record<string, unknown>;
type DeepSeekCaller = (purpose: string, prompt: string, schema: JsonSchema) => Promise<unknown>;

declare const process: {
  env: Record<string, string | undefined>;
};

let testCaller: DeepSeekCaller | null = null;

export function setDeepSeekCallerForTest(caller: DeepSeekCaller | null): void {
  testCaller = caller;
}

export async function callDeepSeek(
  purpose: string,
  prompt: string,
  schema: JsonSchema,
): Promise<unknown> {
  if (testCaller) {
    return testCaller(purpose, prompt, schema);
  }

  const apiKey = process.env.DEEPSEEK_API_KEY;
  if (!apiKey) {
    throw new Error("DEEPSEEK_API_KEY is required.");
  }

  const configuredModels = modelConfig as Record<string, string>;
  const model =
    process.env.PORTAL_ANSWER_MODEL_NAME ||
    process.env.DEEPSEEK_MODEL_NAME ||
    configuredModels[purpose] ||
    "deepseek-v4-pro";

  const response = await fetch("https://api.deepseek.com/chat/completions", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${apiKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      model,
      messages: [
        {
          role: "system",
          content: `You are the ${purpose} agent. Return JSON only. The output must match the provided JSON schema.`,
        },
        {
          role: "user",
          content: `${prompt}\n\nJSON schema:\n${JSON.stringify(schema)}`,
        },
      ],
      response_format: { type: "json_object" },
    }),
  });

  if (!response.ok) {
    throw new Error(`DeepSeek ${purpose} call failed: ${response.status} ${await response.text()}`);
  }

  const payload = await response.json();
  const content = payload?.choices?.[0]?.message?.content;
  if (typeof content !== "string") {
    return content;
  }
  return JSON.parse(content);
}
