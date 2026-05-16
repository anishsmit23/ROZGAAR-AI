import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  Application,
  customizeResume,
  generateEmail,
  getApplications,
  getRankedJobs,
  Job,
  startPipeline,
} from "../api/client";

function formatDate(value: string | null) {
  return value ? new Date(value).toLocaleString() : "-";
}

function formatScore(value: number | null) {
  return value === null ? "-" : value.toFixed(2);
}

export default function DashboardPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [applications, setApplications] = useState<Application[]>([]);
  const [query, setQuery] = useState("Data Scientist");
  const [location, setLocation] = useState("Remote");
  const [remote, setRemote] = useState(true);
  const [limit, setLimit] = useState(25);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const applicationsByJob = useMemo(() => {
    return new Map(applications.map((application) => [application.job_posting_id, application]));
  }, [applications]);

  const refresh = async () => {
    const [jobRows, applicationRows] = await Promise.all([getRankedJobs(), getApplications()]);
    setJobs(jobRows);
    setApplications(applicationRows);
  };

  useEffect(() => {
    refresh().catch((err) => setError(err instanceof Error ? err.message : "Failed to load dashboard"));
  }, []);

  const submitDiscovery = async (event: FormEvent) => {
    event.preventDefault();
    setError("");
    setMessage("");
    setLoading(true);
    try {
      const response = await startPipeline({ query, location, remote, limit });
      setMessage(`Discovery queued. Task: ${response.task_id}`);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start discovery");
    } finally {
      setLoading(false);
    }
  };

  const onCustomize = async (jobId: string) => {
    setError("");
    setMessage("");
    try {
      const response = await customizeResume(jobId);
      setMessage(`Resume customization queued. Task: ${response.task_id}`);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to customize resume");
    }
  };

  const onGenerateEmail = async (jobId: string) => {
    const application = applicationsByJob.get(jobId);
    if (!application) {
      setError("No application exists for this job yet. Customize the resume first.");
      return;
    }
    setError("");
    setMessage("");
    try {
      const response = await generateEmail(application.id);
      setMessage(`Email generation queued. Task: ${response.task_id}`);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to generate email");
    }
  };

  return (
    <div className="space-y-6">
      <section className="panel p-5">
        <div className="mb-4 flex items-center justify-between">
          <div>
            <p className="font-mono text-xs uppercase tracking-[0.2em] text-signal">Pipeline</p>
            <h2 className="text-lg font-semibold">Start Discovery</h2>
          </div>
          <button className="btn" onClick={() => refresh()} type="button">
            Refresh
          </button>
        </div>
        <form className="grid gap-4 md:grid-cols-[1.4fr_1fr_120px_120px_auto]" onSubmit={submitDiscovery}>
          <input className="field" onChange={(e) => setQuery(e.target.value)} placeholder="Role" required value={query} />
          <input className="field" onChange={(e) => setLocation(e.target.value)} placeholder="Location" value={location} />
          <label className="flex items-center gap-2 rounded border border-line bg-ink px-3 text-sm text-slate-300">
            <input checked={remote} onChange={(e) => setRemote(e.target.checked)} type="checkbox" />
            Remote
          </label>
          <input
            className="field"
            max={200}
            min={1}
            onChange={(e) => setLimit(Number(e.target.value))}
            type="number"
            value={limit}
          />
          <button className="btn btn-primary" disabled={loading} type="submit">
            {loading ? "Queuing..." : "Start"}
          </button>
        </form>
      </section>

      {message ? <div className="border border-emerald-900 bg-emerald-950/40 p-3 text-sm text-emerald-200">{message}</div> : null}
      {error ? <div className="border border-red-900 bg-red-950/40 p-3 text-sm text-red-200">{error}</div> : null}

      <section className="panel overflow-hidden">
        <div className="border-b border-line px-5 py-4">
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-slate-500">Ranked Jobs</p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[960px] text-left text-sm">
            <thead className="border-b border-line bg-slate-950 text-xs uppercase text-slate-500">
              <tr>
                <th className="px-4 py-3">Title</th>
                <th className="px-4 py-3">Company</th>
                <th className="px-4 py-3">Location</th>
                <th className="px-4 py-3">semantic_score</th>
                <th className="px-4 py-3">discovered_at</th>
                <th className="px-4 py-3">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {jobs.map((job) => (
                <tr key={job.id} className="hover:bg-slate-900/60">
                  <td className="px-4 py-3 font-medium">{job.title}</td>
                  <td className="px-4 py-3 text-slate-300">{job.company || "-"}</td>
                  <td className="px-4 py-3 text-slate-300">{job.location || "-"}</td>
                  <td className="px-4 py-3 font-mono text-signal">{formatScore(job.semantic_score)}</td>
                  <td className="px-4 py-3 font-mono text-xs text-slate-400">{formatDate(job.discovered_at)}</td>
                  <td className="px-4 py-3">
                    <div className="flex gap-2">
                      <button className="btn" onClick={() => onCustomize(job.id)} type="button">
                        Customize Resume
                      </button>
                      <button className="btn" onClick={() => onGenerateEmail(job.id)} type="button">
                        Generate Email
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {!jobs.length ? (
                <tr>
                  <td className="px-4 py-8 text-center text-slate-500" colSpan={6}>
                    No ranked jobs loaded.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
