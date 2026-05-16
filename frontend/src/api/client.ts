const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "http://localhost:8000").replace(/\/$/, "");
const API_PREFIX = "/api/v1";
const TOKEN_KEY = "rozgaar.jwt";

export type PipelineStartRequest = {
  query: string;
  location?: string | null;
  remote: boolean;
  limit: number;
};

export type PipelineStartResponse = {
  task_id: string;
  run_id: string;
};

export type ApplicationTaskResponse = {
  application_id: string;
  task_id: string;
};

export type Job = {
  id: string;
  title: string;
  company: string | null;
  location: string | null;
  source?: string | null;
  source_url?: string | null;
  semantic_score: number | null;
  discovered_at: string | null;
};

export type ApplicationStage =
  | "DISCOVERED"
  | "RANKED"
  | "RESUME_CUSTOMIZED"
  | "EMAIL_GENERATED"
  | "APPLIED"
  | "ACKNOWLEDGED"
  | "INTERVIEW_SCHEDULED"
  | "CLOSED";

export const APPLICATION_STAGES: ApplicationStage[] = [
  "DISCOVERED",
  "RANKED",
  "RESUME_CUSTOMIZED",
  "EMAIL_GENERATED",
  "APPLIED",
  "ACKNOWLEDGED",
  "INTERVIEW_SCHEDULED",
  "CLOSED",
];

export type Application = {
  id: string;
  job_posting_id: string;
  state: ApplicationStage;
  stage_number: number;
  resume_version_path: string | null;
  email_draft: string | null;
  created_at: string | null;
  updated_at: string | null;
};

export type TaskStatus = {
  task_id: string;
  state: string;
  status?: string | null;
  result: Record<string, unknown> | null;
  error: string | null;
  application_id?: string | null;
  stage?: string | null;
};

export type LoginResponse = {
  access_token: string;
  token_type: string;
};

export type RegisterRequest = {
  full_name: string;
  email: string;
  password: string;
};

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  const token = getToken();

  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let message = `Request failed with HTTP ${response.status}`;
    try {
      const payload = await response.json();
      if (typeof payload.detail === "string") {
        message = payload.detail;
      } else if (payload.detail) {
        message = JSON.stringify(payload.detail);
      }
    } catch {
      const text = await response.text();
      if (text) message = text;
    }
    throw new Error(message);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

export async function login(email: string, password: string): Promise<LoginResponse> {
  const body = new URLSearchParams();
  body.set("username", email.trim().toLowerCase());
  body.set("password", password);

  return request<LoginResponse>(`${API_PREFIX}/auth/jwt/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body,
  });
}

export async function register(payload: RegisterRequest): Promise<unknown> {
  return request<unknown>(`${API_PREFIX}/auth/register`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      email: payload.email.trim().toLowerCase(),
      password: payload.password,
      full_name: payload.full_name.trim() || null,
    }),
  });
}

export async function startPipeline(payload: PipelineStartRequest): Promise<PipelineStartResponse> {
  return request<PipelineStartResponse>(`${API_PREFIX}/pipeline/start`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
}

export async function getRankedJobs(): Promise<Job[]> {
  return request<Job[]>(`${API_PREFIX}/jobs/ranked?limit=100&offset=0`);
}

export async function customizeResume(jobId: string): Promise<ApplicationTaskResponse> {
  return request<ApplicationTaskResponse>(`${API_PREFIX}/resume/customize`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ job_id: jobId }),
  });
}

export async function generateEmail(applicationId: string): Promise<ApplicationTaskResponse> {
  return request<ApplicationTaskResponse>(`${API_PREFIX}/email/generate`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ application_id: applicationId }),
  });
}

export async function getApplications(): Promise<Application[]> {
  return request<Application[]>(`${API_PREFIX}/applications?limit=200&offset=0`);
}

export async function getTaskStatus(taskId: string): Promise<TaskStatus> {
  return request<TaskStatus>(`${API_PREFIX}/tasks/${encodeURIComponent(taskId)}/status`);
}

export function getTaskStatusStreamUrl(taskId: string): string {
  return `${API_BASE_URL}${API_PREFIX}/tasks/${encodeURIComponent(taskId)}/stream`;
}

export async function downloadResume(applicationId: string): Promise<string> {
  const payload = await request<{ download_url: string }>(
    `${API_PREFIX}/applications/${encodeURIComponent(applicationId)}/resume/download`,
  );
  return payload.download_url;
}
