import { callGemini } from "../clients/gemini";
import stage1Schema from "../schemas/stage1.schema.json";
import { validate } from "../schemas/validate";
import { Stage1Job } from "../types";
import { buildStage1Prompt } from "../prompts/stage1_prompt";

export async function runStage1(rawJobs: string[]): Promise<Stage1Job[]> {
  const prompt = buildStage1Prompt(rawJobs);
  const raw = await callGemini("stage1", prompt, stage1Schema, { arrayMode: true });
  if (!Array.isArray(raw)) {
    throw new Error("Stage 1 response must be an array.");
  }
  return raw.map((item: unknown) => validate<Stage1Job>(item, stage1Schema));
}
