import { runStage2 } from "../agents/stage2";
import { setGeminiCallerForTest } from "../clients/gemini";

async function testStage2ReturnsStructuredDossier(): Promise<void> {
  setGeminiCallerForTest(async () => ({
    job_id: "123",
    firm_name: "Law Firm",
    role_title: "Paralegal",
    culture: "test",
    values: "test",
    training: "test",
    recruitment: "test",
    commercial_awareness: "test",
    practice_areas: "test",
    clients: "test",
    risks: "test",
    application_strategy: "test",
    interview_strategy: "test",
    competency_mapping: "test",
    tone_guidance: "test",
  }));

  const fakeJob = {
    job_id: "123",
    title: "Paralegal",
    employer: "Law Firm",
    location: "London",
    url: "http://example.com",
  };

  const result = await runStage2(fakeJob);
  expectHas(result, "culture");
  expectHas(result, "application_strategy");
  expectHas(result, "interview_strategy");

  setGeminiCallerForTest(null);
}

function expectHas(value: Record<string, unknown>, key: string): void {
  if (!(key in value)) {
    throw new Error(`Expected result to have property ${key}`);
  }
}

void testStage2ReturnsStructuredDossier();
