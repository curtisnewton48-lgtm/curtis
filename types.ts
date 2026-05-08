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
