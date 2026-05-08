import { runPortalAgent } from "../agents/portal_agent";
import { setDeepSeekCallerForTest } from "../clients/deepseek";

async function testPortalAgentReturnsStructuredAnswers(): Promise<void> {
  setDeepSeekCallerForTest(async () => ({
    answers: [
      {
        question: "Describe a time you showed teamwork (250 words)",
        answer: "I contributed to a team project by coordinating tasks, communicating clearly, and helping the group deliver a strong result.",
        word_count: 24,
        competency: "teamwork",
        star_source: "Teamwork STAR 1",
        notes: "Uses teamwork example and should be expanded with a real result before submission.",
      },
    ],
  }));

  const fakeQuestions = [{ question: "Describe a time you showed teamwork (250 words)" }];
  const fakeDossier = {
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
  };
  const fakeStarBank = { stars: [] };
  const fakeCv = { experience: [] };

  const result = await runPortalAgent(fakeQuestions, fakeDossier, fakeStarBank, fakeCv);
  expect(Boolean(result.answers), true);
  expect(Array.isArray(result.answers), true);
  expect(result.answers[0].competency, "teamwork");

  setDeepSeekCallerForTest(null);
}

function expect(actual: unknown, expected: unknown): void {
  if (actual !== expected) {
    throw new Error(`Expected ${String(expected)}, got ${String(actual)}`);
  }
}

void testPortalAgentReturnsStructuredAnswers();
