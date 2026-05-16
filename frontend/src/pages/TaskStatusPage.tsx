import { FormEvent, useEffect, useMemo, useState } from "react";
import { getTaskStatusStreamUrl, TaskStatus } from "../api/client";

const TERMINAL_STATES = new Set(["SUCCESS", "FAILURE", "REVOKED", "TIMEOUT"]);

export default function TaskStatusPage() {
  const [taskId, setTaskId] = useState("");
  const [activeTaskId, setActiveTaskId] = useState("");
  const [status, setStatus] = useState<TaskStatus | null>(null);
  const [error, setError] = useState("");
  const [connected, setConnected] = useState(false);

  const isWaiting = useMemo(() => {
    return Boolean(activeTaskId) && (!status || !TERMINAL_STATES.has(status.state));
  }, [activeTaskId, status]);

  const submit = (event: FormEvent) => {
    event.preventDefault();
    setStatus(null);
    setError("");
    setConnected(false);
    setActiveTaskId(taskId.trim());
  };

  useEffect(() => {
    if (!activeTaskId) return;

    const source = new EventSource(getTaskStatusStreamUrl(activeTaskId));

    source.onopen = () => {
      setConnected(true);
      setError("");
    };

    source.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data) as Partial<TaskStatus>;
        const nextStatus: TaskStatus = {
          task_id: activeTaskId,
          state: payload.state || "UNKNOWN",
          status: payload.status || payload.state || "UNKNOWN",
          result: payload.result || null,
          error: payload.error || null,
          application_id: payload.application_id || null,
          stage: payload.stage || null,
        };
        setStatus(nextStatus);

        if (TERMINAL_STATES.has(nextStatus.state)) {
          source.close();
          setConnected(false);
        }
      } catch {
        setError("Received an invalid task status event.");
      }
    };

    source.onerror = () => {
      if (!status || !TERMINAL_STATES.has(status.state)) {
        setError("Task status stream disconnected.");
      }
      source.close();
      setConnected(false);
    };

    return () => {
      source.close();
      setConnected(false);
    };
  }, [activeTaskId]);

  return (
    <div className="space-y-5">
      <section className="panel p-5">
        <p className="font-mono text-xs uppercase tracking-[0.2em] text-signal">Celery</p>
        <h2 className="mt-1 text-xl font-semibold">Task Status Stream</h2>
        <form className="mt-5 flex flex-col gap-3 md:flex-row" onSubmit={submit}>
          <input
            className="field"
            onChange={(event) => setTaskId(event.target.value)}
            placeholder="Paste task_id"
            value={taskId}
          />
          <button className="btn btn-primary md:w-36" disabled={!taskId.trim()} type="submit">
            Track
          </button>
        </form>
      </section>

      {error ? <div className="border border-red-900 bg-red-950/40 p-3 text-sm text-red-200">{error}</div> : null}

      <section className="panel p-5">
        <div className="grid gap-4 md:grid-cols-4">
          <div>
            <p className="font-mono text-xs uppercase text-slate-500">task_id</p>
            <p className="mt-2 break-all text-sm">{status?.task_id || activeTaskId || "-"}</p>
          </div>
          <div>
            <p className="font-mono text-xs uppercase text-slate-500">state</p>
            <div className="mt-2 flex items-center gap-3">
              {isWaiting ? <span className="h-4 w-4 animate-spin rounded-full border-2 border-signal border-t-transparent" /> : null}
              <p className="font-mono text-2xl text-signal">{status?.state || (activeTaskId ? "WAITING" : "-")}</p>
            </div>
          </div>
          <div>
            <p className="font-mono text-xs uppercase text-slate-500">stage</p>
            <p className="mt-2 font-mono text-sm text-slate-300">{status?.stage || "-"}</p>
          </div>
          <div>
            <p className="font-mono text-xs uppercase text-slate-500">stream</p>
            <p className="mt-2 text-sm text-slate-300">
              {connected ? "Connected" : activeTaskId ? "Closed" : "Waiting for task ID"}
            </p>
          </div>
        </div>
        <div className="mt-5 border border-line bg-ink p-4">
          <p className="mb-2 font-mono text-xs uppercase text-slate-500">Latest Event</p>
          <pre className="overflow-auto text-xs text-slate-300">
            {JSON.stringify(
              {
                state: status?.state || null,
                error: status?.error || null,
                application_id: status?.application_id || null,
                stage: status?.stage || null,
              },
              null,
              2,
            )}
          </pre>
        </div>
      </section>
    </div>
  );
}
