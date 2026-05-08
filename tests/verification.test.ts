import { validate } from "../schemas/validate";
import verificationSchema from "../schemas/verification.schema.json";
import { VerificationResult } from "../types";

const result = validate<VerificationResult>(
  {
    job_id: "job-1",
    is_valid: true,
    validity_reason: "The supplied URL and description appear to describe an open paralegal vacancy.",
    fixed_fields: {
      title: "Paralegal",
      employer: "Example LLP",
      location: "Manchester",
      deadline: null,
      url: "https://example.com/jobs/1",
    },
    flags: ["missing deadline"],
  },
  verificationSchema,
);

expectEqual(result.job_id, "job-1");
expectEqual(result.is_valid, true);
expectEqual(result.fixed_fields.employer, "Example LLP");

function expectEqual(actual: unknown, expected: unknown): void {
  if (actual !== expected) {
    throw new Error(`Expected ${String(expected)}, got ${String(actual)}`);
  }
}
