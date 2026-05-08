import { callMistral } from "../clients/mistral";
import verificationSchema from "../schemas/verification.schema.json";
import { validate } from "../schemas/validate";
import { Stage1Job, VerificationResult } from "../types";

export async function runVerification(job: Stage1Job): Promise<VerificationResult> {
  const prompt = buildVerificationPrompt(job);
  const raw = await callMistral("verification", prompt, verificationSchema);
  return validate<VerificationResult>(raw, verificationSchema);
}

function buildVerificationPrompt(job: Stage1Job): string {
  return `
You are a job verification agent.

Your tasks:
1. Determine if this job appears real and currently open.
2. Check and correct if possible:
   - job title
   - employer name
   - location
   - application deadline
   - job URL
3. Identify issues such as:
   - expired
   - duplicate
   - suspicious
   - missing fields
   - location mismatch
4. Output JSON ONLY matching this schema.

Rules:
- Set is_valid=false for advice articles, stale listing pages, expired jobs, impossible URLs, or suspicious/non-job pages.
- Use fixed_fields to provide corrected values when you can verify or infer them from the supplied text.
- Use null for any fixed field that cannot be corrected confidently.
- Keep validity_reason concise and evidence-based.

Job:
${JSON.stringify(job, null, 2)}
`;
}
