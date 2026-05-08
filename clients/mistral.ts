type JsonSchema = Record<string, unknown>;

declare const process: {
  env: Record<string, string | undefined>;
};

interface MistralMessage {
  role: "system" | "user";
  content: string;
}

export async function callMistral(
  purpose: string,
  prompt: string,
  schema: JsonSchema,
): Promise<unknown> {
  const apiKey = process.env.MISTRAL_API_KEY;
  if (!apiKey) {
    throw new Error("MISTRAL_API_KEY is required.");
  }

  const model = process.env.VERIFICATION_MODEL_NAME || process.env.MICRO_AGENT_MODEL_NAME || "ministral-8b-2512";
  const messages: MistralMessage[] = [
    {
      role: "system",
      content: `You are the ${purpose} agent. Return JSON only. The output must match the provided JSON schema.`,
    },
    {
      role: "user",
      content: `${prompt}\n\nJSON schema:\n${JSON.stringify(schema)}`,
    },
  ];

  const response = await fetch("https://api.mistral.ai/v1/chat/completions", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${apiKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      model,
      messages,
      response_format: { type: "json_object" },
    }),
  });

  if (!response.ok) {
    throw new Error(`Mistral ${purpose} call failed: ${response.status} ${await response.text()}`);
  }

  const payload = await response.json();
  const content = payload?.choices?.[0]?.message?.content;
  if (typeof content !== "string") {
    return content;
  }
  return JSON.parse(content);
}
