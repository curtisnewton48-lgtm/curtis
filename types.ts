export interface Stage1Job {
  job_id: string;
  title?: string | null;
  employer?: string | null;
  company?: string | null;
  location?: string | null;
  deadline?: string | null;
  application_deadline?: string | null;
  url?: string | null;
  description?: string | null;
  raw_description?: string | null;
  source?: string | null;
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
  culture?: unknown;
  competencies?: unknown;
  application_strategy?: unknown;
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
