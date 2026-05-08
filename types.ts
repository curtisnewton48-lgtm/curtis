export interface Stage1Job {
  job_id: string;
  title: string;
  employer: string;
  company?: string | null;
  location: string;
  deadline?: string | null;
  application_deadline?: string | null;
  url: string;
  description?: string | null;
  raw_description: string;
  source: string;
  [key: string]: unknown;
}

export interface VerificationResult {
  job_id: string;
  is_valid: boolean;
  validity_reason: string;
  fixed_fields: {
    title: string | null;
    employer: string | null;
    location: string | null;
    deadline: string | null;
    url: string | null;
  };
  flags: string[];
}

export interface VerifiedJob extends Stage1Job {
  verification: VerificationResult;
  is_valid: boolean;
}

export interface PortalQuestion {
  question: string;
}

export interface PortalAnswer {
  question: string;
  answer: string;
  word_count: number;
  competency: string;
  star_source: string;
  notes: string;
}

export interface PortalAnswers {
  answers: PortalAnswer[];
}

export interface Stage2Dossier {
  job_id: string;
  firm_name: string;
  role_title: string;
  culture: string;
  values: string;
  training: string;
  recruitment: string;
  commercial_awareness: string;
  practice_areas: string;
  clients: string;
  risks: string;
  application_strategy: string;
  interview_strategy: string;
  competency_mapping: string;
  tone_guidance: string;
  [key: string]: unknown;
}

export interface CvOutput {
  [key: string]: unknown;
}

export interface StarBank {
  stars?: unknown;
  content?: unknown;
  [key: string]: unknown;
}

export interface MasterCV {
  experience?: unknown;
  education?: unknown;
  skills?: unknown;
  [key: string]: unknown;
}
