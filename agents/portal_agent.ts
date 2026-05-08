import { callDeepSeek } from "../clients/deepseek";
import portalSchema from "../schemas/portal_agent.schema.json";
import { validate } from "../schemas/validate";
import { Stage2Dossier, PortalQuestion, PortalAnswers, StarBank, MasterCV } from "../types";

export async function runPortalAgent(
  questions: PortalQuestion[],
  dossier: Stage2Dossier,
  starBank: StarBank,
  masterCv: MasterCV,
): Promise<PortalAnswers> {
  const prompt = buildPortalPrompt(questions, dossier, starBank, masterCv);
  const raw = await callDeepSeek("portal_agent", prompt, portalSchema);
  return validate<PortalAnswers>(raw, portalSchema);
}

function buildPortalPrompt(
  questions: PortalQuestion[],
  dossier: Stage2Dossier,
  starBank: StarBank,
  masterCv: MasterCV,
): string {
  return `
You are the Application-Form Answer Agent.

Your job:
- Write tailored, firm-specific answers to application-form questions.
- Use the Stage-2 research dossier for culture, competencies, values, commercial awareness, and application strategy.
- Use the STAR bank to select and rewrite the most relevant STAR example.
- Use the Master CV for additional evidence.
- Match tone to the employer type (corporate, public sector, charity, litigation, commercial).
- Respect word limits if provided in the question text.
- Avoid cliches, generic statements, and invented details.

For EACH question, you must:
1. Identify the competency being tested.
2. Select the best STAR example from the STAR bank.
3. Rewrite the STAR to match the question.
4. Integrate firm-specific insights from the Stage-2 dossier.
5. Produce a polished, concise answer.
6. Provide:
   - question
   - final answer
   - word_count
   - competency
   - star_source (which STAR was used)
   - notes (hidden reasoning, not part of the final answer)

Output JSON ONLY matching this schema:
{
  "answers": [
    {
      "question": string,
      "answer": string,
      "word_count": number,
      "competency": string,
      "star_source": string,
      "notes": string
    }
  ]
}

Here are the inputs:

QUESTIONS:
${JSON.stringify(questions, null, 2)}

STAGE-2 DOSSIER:
${JSON.stringify(dossier, null, 2)}

STAR BANK:
${JSON.stringify(starBank, null, 2)}

MASTER CV:
${JSON.stringify(masterCv, null, 2)}
`;
}
