import { runStage1 } from "./agents/stage1";
import { runVerification } from "./agents/verification";
import { runPortalAgent } from "./agents/portal_agent";
import { runStage2 } from "./agents/stage2";
import { CvOutput, MasterCV, PortalQuestion, Stage1Job, Stage2Dossier, StarBank, VerifiedJob } from "./types";

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
    employer: fixedFields.employer ?? job.employer,
    location: fixedFields.location ?? job.location,
    ...(fixedFields.deadline ? { deadline: fixedFields.deadline } : {}),
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

export async function processJob(rawJob: string, masterCv: MasterCV) {
  const [job] = await runStage1([rawJob]);
  const verification = await runVerification(job);

  if (!verification.is_valid) {
    return { status: "rejected_by_verification", job, verification };
  }

  const verifiedJob = {
    ...job,
    ...Object.fromEntries(
      Object.entries(verification.fixed_fields).filter(([, value]) => value !== null),
    ),
  };

  const dossier = await runStage2(verifiedJob);
  const cv = await runCvAgent(masterCv, dossier);

  return {
    status: "ready",
    job: verifiedJob,
    verification,
    dossier,
    cv,
  };
}

async function runCvAgent(masterCv: MasterCV, dossier: Stage2Dossier): Promise<CvOutput> {
  return {
    status: "cv_ready",
    masterCv,
    dossier,
  };
}
