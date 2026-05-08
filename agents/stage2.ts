import { callGemini } from "../clients/gemini";
import stage2Schema from "../schemas/stage2.schema.json";
import { validate } from "../schemas/validate";
import { Stage1Job, Stage2Dossier } from "../types";
import { buildStage2Prompt } from "../prompts/stage2_prompt";

export async function runStage2(job: Stage1Job): Promise<Stage2Dossier> {
  const prompt = buildStage2Prompt(job);
  const raw = await callGemini("stage2", prompt, stage2Schema);
  return validate<Stage2Dossier>(raw, stage2Schema);
}
