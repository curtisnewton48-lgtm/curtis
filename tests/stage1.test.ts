import { runStage1 } from "../agents/stage1";
import { setGeminiCallerForTest } from "../clients/gemini";

async function testStage1ReturnsStructuredJobObjects(): Promise<void> {
  setGeminiCallerForTest(async () => [
    {
      job_id: "123",
      title: "Paralegal",
      employer: "Law Firm",
      location: "London",
      url: "http://example.com",
      raw_description: "Paralegal role at Law Firm in London",
      source: "test",
    },
  ]);

  const fakeRawJobs = ["Paralegal role at Law Firm in London"];
  const result = await runStage1(fakeRawJobs);

  expect(Array.isArray(result), true);
  expectHas(result[0], "title");
  expectHas(result[0], "employer");
  expectHas(result[0], "location");

  setGeminiCallerForTest(null);
}

function expect(actual: unknown, expected: unknown): void {
  if (actual !== expected) {
    throw new Error(`Expected ${String(expected)}, got ${String(actual)}`);
  }
}

function expectHas(value: Record<string, unknown>, key: string): void {
  if (!(key in value)) {
    throw new Error(`Expected result to have property ${key}`);
  }
}

void testStage1ReturnsStructuredJobObjects();
