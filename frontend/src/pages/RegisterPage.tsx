import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { register } from "../api/client";

export default function RegisterPage() {
  const navigate = useNavigate();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setError("");
    setLoading(true);
    try {
      await register({ full_name: fullName, email, password });
      navigate("/login");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="flex min-h-screen items-center justify-center bg-ink px-4 text-slate-100">
      <section className="panel w-full max-w-md p-6">
        <p className="font-mono text-xs uppercase tracking-[0.24em] text-signal">Rozgaar AI</p>
        <h1 className="mt-2 text-2xl font-semibold">Create account</h1>
        <form className="mt-6 space-y-4" onSubmit={submit}>
          <label className="block">
            <span className="mb-1 block text-sm text-slate-400">Name</span>
            <input className="field" onChange={(e) => setFullName(e.target.value)} required value={fullName} />
          </label>
          <label className="block">
            <span className="mb-1 block text-sm text-slate-400">Email</span>
            <input className="field" onChange={(e) => setEmail(e.target.value)} required type="email" value={email} />
          </label>
          <label className="block">
            <span className="mb-1 block text-sm text-slate-400">Password</span>
            <input
              className="field"
              minLength={8}
              onChange={(e) => setPassword(e.target.value)}
              required
              type="password"
              value={password}
            />
          </label>
          {error ? <div className="border border-red-900 bg-red-950/40 p-3 text-sm text-red-200">{error}</div> : null}
          <button className="btn btn-primary w-full" disabled={loading} type="submit">
            {loading ? "Creating..." : "Register"}
          </button>
        </form>
        <p className="mt-5 text-sm text-slate-400">
          Already registered?{" "}
          <Link className="text-signal hover:text-emerald-300" to="/login">
            Sign in
          </Link>
        </p>
      </section>
    </main>
  );
}
