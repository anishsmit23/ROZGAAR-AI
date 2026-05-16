import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { login, setToken } from "../api/client";

export default function LoginPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setError("");
    setLoading(true);
    try {
      const response = await login(email, password);
      setToken(response.access_token);
      navigate("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="flex min-h-screen items-center justify-center bg-ink px-4 text-slate-100">
      <section className="panel w-full max-w-md p-6">
        <p className="font-mono text-xs uppercase tracking-[0.24em] text-signal">Rozgaar AI</p>
        <h1 className="mt-2 text-2xl font-semibold">Sign in</h1>
        <form className="mt-6 space-y-4" onSubmit={submit}>
          <label className="block">
            <span className="mb-1 block text-sm text-slate-400">Email</span>
            <input className="field" onChange={(e) => setEmail(e.target.value)} required type="email" value={email} />
          </label>
          <label className="block">
            <span className="mb-1 block text-sm text-slate-400">Password</span>
            <input
              className="field"
              onChange={(e) => setPassword(e.target.value)}
              required
              type="password"
              value={password}
            />
          </label>
          {error ? <div className="border border-red-900 bg-red-950/40 p-3 text-sm text-red-200">{error}</div> : null}
          <button className="btn btn-primary w-full" disabled={loading} type="submit">
            {loading ? "Signing in..." : "Login"}
          </button>
        </form>
        <p className="mt-5 text-sm text-slate-400">
          New here?{" "}
          <Link className="text-signal hover:text-emerald-300" to="/register">
            Create an account
          </Link>
        </p>
      </section>
    </main>
  );
}
