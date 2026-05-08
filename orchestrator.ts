import { runVerification } from "./agents/verification";
import { runPortalAgent } from "./agents/portal_agent";
import { MasterCV, PortalQuestion, Stage1Job, Stage2Dossier, StarBank, VerifiedJob } from "./types";

export async function processStage1Jobs(jobs: Stage1Job[]): Promise<VerifiedJob[]> {
  const verifiedJobs: VerifiedJob[] = [];

  for (const job of jobs) {
    const verification = await runVerification(job);
    verifiedJobs.push({
      ...applyFixedFields(job, verification.fixed_fields),
      verification,
      is_valid: verification.is_valid,
    });
  }

  return verifiedJobs;
}

function applyFixedFields(
  job: Stage1Job,
  fixedFields: VerifiedJob["verification"]["fixed_fields"],
): Stage1Job {
  return {
    ...job,
    title: fixedFields.title ?? job.title,
    employer: fixedFields.employer ?? job.employer ?? job.company,
    location: fixedFields.location ?? job.location,
    deadline: fixedFields.deadline ?? job.deadline ?? job.application_deadline,
    url: fixedFields.url ?? job.url,
  };
}

export async function processPortalApplication(
  questions: PortalQuestion[],
  dossier: Stage2Dossier,
  starBank: StarBank,
  masterCv: MasterCV,
) {
  const answers = await runPortalAgent(questions, dossier, starBank, masterCv);

  return {
    status: "portal_answers_ready",
    answers,
  };
}
