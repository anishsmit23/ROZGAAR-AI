import { useEffect, useMemo, useState } from "react";
import {
  APPLICATION_STAGES,
  Application,
  ApplicationStage,
  downloadResume,
  getApplications,
  getRankedJobs,
  Job,
} from "../api/client";

function titleCaseStage(stage: string) {
  return stage.replace(/_/g, " ");
}

export default function ApplicationsPage() {
  const [applications, setApplications] = useState<Application[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [error, setError] = useState("");

  const jobsById = useMemo(() => new Map(jobs.map((job) => [job.id, job])), [jobs]);
  const grouped = useMemo(() => {
    const buckets = new Map<ApplicationStage, Application[]>();
    APPLICATION_STAGES.forEach((stage) => buckets.set(stage, []));
    applications.forEach((application) => {
      buckets.get(application.state)?.push(application);
    });
    return buckets;
  }, [applications]);

  const refresh = async () => {
    setError("");
    try {
      const [applicationRows, jobRows] = await Promise.all([getApplications(), getRankedJobs()]);
      setApplications(applicationRows);
      setJobs(jobRows);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load applications");
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  const onDownload = async (applicationId: string) => {
    try {
      const url = await downloadResume(applicationId);
      window.open(url, "_blank", "noopener,noreferrer");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Resume download failed");
    }
  };

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-signal">Applications</p>
          <h2 className="text-xl font-semibold">Stage Board</h2>
        </div>
        <button className="btn" onClick={refresh} type="button">
          Refresh
        </button>
      </div>

      {error ? <div className="border border-red-900 bg-red-950/40 p-3 text-sm text-red-200">{error}</div> : null}

      <section className="grid gap-3 overflow-x-auto pb-2 lg:grid-cols-4 xl:grid-cols-8">
        {APPLICATION_STAGES.map((stage) => {
          const stageApplications = grouped.get(stage) || [];
          return (
            <div className="panel min-h-[420px] min-w-[230px]" key={stage}>
              <div className="border-b border-line px-3 py-3">
                <div className="flex items-center justify-between gap-3">
                  <h3 className="text-sm font-semibold">{titleCaseStage(stage)}</h3>
                  <span className="font-mono text-xs text-slate-500">{stageApplications.length}</span>
                </div>
              </div>
              <div className="space-y-3 p-3">
                {stageApplications.map((application) => {
                  const job = jobsById.get(application.job_posting_id);
                  return (
                    <article className="border border-line bg-ink p-3" key={application.id}>
                      <p className="text-sm font-medium">{job?.title || `Job ${application.job_posting_id.slice(0, 8)}`}</p>
                      <p className="mt-1 text-xs text-slate-500">{job?.company || "Company unavailable"}</p>
                      <p className="mt-3 font-mono text-[11px] uppercase text-signal">{application.state}</p>
                      {application.state === "RESUME_CUSTOMIZED" && application.resume_version_path ? (
                        <button
                          className="mt-3 text-left text-xs text-signal hover:text-emerald-300"
                          onClick={() => onDownload(application.id)}
                          type="button"
                        >
                          Download Resume
                        </button>
                      ) : null}
                    </article>
                  );
                })}
                {!stageApplications.length ? <p className="py-4 text-center text-xs text-slate-600">Empty</p> : null}
              </div>
            </div>
          );
        })}
      </section>
    </div>
  );
}
