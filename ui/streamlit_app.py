from __future__ import annotations

import os
from collections import Counter
from pathlib import Path
from typing import Any

import httpx
import streamlit as st


PUBLIC_API_URL = os.getenv("PUBLIC_API_URL", "http://127.0.0.1:8000").rstrip("/")
PUBLIC_API_DISPLAY_URL = os.getenv("PUBLIC_API_DISPLAY_URL", "http://localhost:8000").rstrip("/")
API_PREFIX = "/api/v1"
PROJECT_ROOT = Path(__file__).resolve().parents[1]

EXCLUDED_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".streamlit",
    ".venv",
    "__pycache__",
    "htmlcov",
    "myenv",
    "node_modules",
}
EXCLUDED_SUFFIXES = {
    ".db",
    ".html",
    ".ico",
    ".jpg",
    ".jpeg",
    ".pem",
    ".png",
    ".pyc",
    ".sqlite",
    ".woff",
    ".woff2",
}
TEXT_SUFFIXES = {
    ".cfg",
    ".css",
    ".env",
    ".example",
    ".ini",
    ".js",
    ".json",
    ".md",
    ".py",
    ".sh",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}
APPLICATION_STAGES = [
    "DISCOVERED",
    "RANKED",
    "RESUME_CUSTOMIZED",
    "EMAIL_GENERATED",
    "APPLIED",
    "ACKNOWLEDGED",
    "INTERVIEW_SCHEDULED",
    "CLOSED",
]


st.set_page_config(page_title="Rozgaar AI", page_icon="R", layout="wide")


def api_url(path: str) -> str:
    if path.startswith("http"):
        return path
    return f"{PUBLIC_API_URL}{path}"


def auth_headers() -> dict[str, str]:
    token = st.session_state.get("access_token")
    return {"Authorization": f"Bearer {token}"} if token else {}


def request_api(
    method: str,
    path: str,
    *,
    json: dict[str, Any] | None = None,
    data: dict[str, Any] | None = None,
    auth: bool = True,
    timeout: float = 15,
) -> tuple[dict[str, Any] | list[Any] | str | None, str | None, int | None]:
    headers = auth_headers() if auth else {}
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.request(method, api_url(path), json=json, data=data, headers=headers)
        if response.status_code >= 400:
            return None, readable_error(response), response.status_code
        if not response.content:
            return None, None, response.status_code
        try:
            return response.json(), None, response.status_code
        except ValueError:
            return response.text, None, response.status_code
    except Exception as exc:
        return None, str(exc), None


def readable_error(response: httpx.Response) -> str:
    try:
        detail = response.json()
    except ValueError:
        return response.text or f"HTTP {response.status_code}"
    if isinstance(detail, dict) and "detail" in detail:
        return str(detail["detail"])
    return str(detail)


def require_login() -> bool:
    if st.session_state.get("access_token"):
        return True
    st.info("Sign in to use the job-agent workflow.")
    return False


def render_header() -> None:
    left, right = st.columns([0.72, 0.28])
    with left:
        st.title("Rozgaar AI")
        st.caption("Job-agent dashboard plus local project analyzer")
    with right:
        health, error, _ = request_api("GET", "/health", auth=False, timeout=5)
        if error:
            st.error(f"API offline: {error}")
        else:
            st.success(f"API {health.get('status', 'ok') if isinstance(health, dict) else 'ok'}")
        st.caption(PUBLIC_API_DISPLAY_URL)


def render_auth_panel() -> None:
    with st.sidebar:
        st.header("Session")
        if st.session_state.get("access_token"):
            st.success("Signed in")
            if st.button("Logout", use_container_width=True):
                for key in ["access_token", "token_type", "last_task_id", "last_run_id"]:
                    st.session_state.pop(key, None)
                st.rerun()
            return

        login_tab, register_tab = st.tabs(["Login", "Register"])
        with login_tab:
            with st.form("login_form"):
                email = st.text_input("Email", key="login_email")
                password = st.text_input("Password", type="password", key="login_password")
                submitted = st.form_submit_button("Login", use_container_width=True)
            if submitted:
                payload = {"username": email, "password": password}
                result, error, _ = request_api(
                    "POST",
                    f"{API_PREFIX}/auth/jwt/login",
                    data=payload,
                    auth=False,
                )
                if error:
                    st.error(error)
                elif isinstance(result, dict) and result.get("access_token"):
                    st.session_state["access_token"] = result["access_token"]
                    st.session_state["token_type"] = result.get("token_type", "bearer")
                    st.success("Logged in")
                    st.rerun()
                else:
                    st.error("Login response did not include an access token.")

        with register_tab:
            with st.form("register_form"):
                email = st.text_input("Email", key="register_email")
                password = st.text_input("Password", type="password", key="register_password")
                full_name = st.text_input("Full name")
                skills = st.text_input("Skills", placeholder="Python, FastAPI, SQL")
                experience = st.number_input("Experience years", min_value=0, max_value=60, value=0)
                submitted = st.form_submit_button("Create account", use_container_width=True)
            if submitted:
                payload = {
                    "email": email,
                    "password": password,
                    "full_name": full_name or None,
                    "skills": [s.strip() for s in skills.split(",") if s.strip()] or None,
                    "experience_years": int(experience),
                }
                _, error, _ = request_api(
                    "POST",
                    f"{API_PREFIX}/auth/register",
                    json=payload,
                    auth=False,
                )
                if error:
                    st.error(error)
                else:
                    st.success("Account created. You can log in now.")


def render_discover_tab() -> None:
    st.subheader("Discover Jobs")
    if not require_login():
        return

    with st.form("pipeline_start"):
        col1, col2, col3, col4 = st.columns([0.35, 0.3, 0.18, 0.17])
        with col1:
            query = st.text_input("Target role", value="Data Scientist")
        with col2:
            location = st.text_input("Location", value="Remote")
        with col3:
            remote = st.checkbox("Remote only", value=True)
        with col4:
            limit = st.number_input("Limit", min_value=1, max_value=200, value=25)
        submitted = st.form_submit_button("Start discovery")

    if submitted:
        payload = {"query": query, "location": location or None, "remote": remote, "limit": int(limit)}
        result, error, _ = request_api("POST", f"{API_PREFIX}/pipeline/start", json=payload)
        if error:
            st.error(error)
            return
        if isinstance(result, dict):
            st.session_state["last_task_id"] = result.get("task_id")
            st.session_state["last_run_id"] = result.get("run_id")
            st.success("Discovery queued")
            st.json(result)


def render_tasks_tab() -> None:
    st.subheader("Task Status")
    if not require_login():
        return

    default_task = st.session_state.get("last_task_id", "")
    task_id = st.text_input("Task ID", value=default_task)
    col1, col2 = st.columns([0.2, 0.8])
    with col1:
        refresh = st.button("Check status", use_container_width=True)
    with col2:
        if st.session_state.get("last_run_id"):
            st.caption(f"Last run: {st.session_state['last_run_id']}")

    if refresh and task_id:
        result, error, _ = request_api("GET", f"{API_PREFIX}/tasks/{task_id}/status")
        if error:
            st.error(error)
            return
        if isinstance(result, dict):
            status = result.get("status", "UNKNOWN")
            st.metric("Status", status)
            if result.get("error"):
                st.error(result["error"])
            if result.get("result"):
                st.json(result["result"])
            else:
                st.json(result)


def render_jobs_tab() -> None:
    st.subheader("Jobs")
    if not require_login():
        return

    col1, col2, col3, col4 = st.columns([0.22, 0.3, 0.22, 0.26])
    with col1:
        ranked = st.toggle("Ranked only", value=True)
    with col2:
        company = st.text_input("Company filter")
    with col3:
        limit = st.number_input("Rows", min_value=1, max_value=200, value=50, key="jobs_limit")
    with col4:
        load = st.button("Load jobs", use_container_width=True)

    if load:
        endpoint = f"{API_PREFIX}/jobs/ranked" if ranked else f"{API_PREFIX}/jobs"
        params = f"?limit={int(limit)}&offset=0"
        if company and not ranked:
            params += f"&company={company}"
        result, error, _ = request_api("GET", f"{endpoint}{params}")
        if error:
            st.error(error)
            return
        st.session_state["jobs"] = result if isinstance(result, list) else []

    jobs = st.session_state.get("jobs", [])
    if not jobs:
        st.info("No jobs loaded yet.")
        return

    st.dataframe(jobs, use_container_width=True, hide_index=True)
    st.divider()
    st.caption("Actions")
    for job in jobs[:20]:
        title = job.get("title") or "Untitled role"
        company_name = job.get("company") or "Unknown company"
        score = job.get("semantic_score")
        label = f"{title} at {company_name}"
        with st.expander(label):
            st.write(job)
            action_col1, action_col2, action_col3 = st.columns([0.25, 0.25, 0.5])
            with action_col1:
                if st.button("Tailor resume", key=f"resume_{job.get('id')}"):
                    payload = {"job_id": job.get("id")}
                    result, error, _ = request_api("POST", f"{API_PREFIX}/resume/customize", json=payload)
                    if error:
                        st.error(error)
                    else:
                        st.success("Resume customization queued")
                        st.json(result)
            with action_col2:
                if job.get("source_url"):
                    st.link_button("Open source", job["source_url"])
            with action_col3:
                if score is not None:
                    st.metric("Semantic score", f"{float(score):.2f}")


def render_applications_tab() -> None:
    st.subheader("Applications")
    if not require_login():
        return

    col1, col2, col3 = st.columns([0.25, 0.25, 0.5])
    with col1:
        state = st.selectbox("State", ["ALL", *APPLICATION_STAGES])
    with col2:
        limit = st.number_input("Rows", min_value=1, max_value=200, value=50, key="apps_limit")
    with col3:
        load = st.button("Load applications", use_container_width=True)

    if load:
        path = f"{API_PREFIX}/applications?limit={int(limit)}&offset=0"
        if state != "ALL":
            path += f"&state={state}"
        result, error, _ = request_api("GET", path)
        if error:
            st.error(error)
            return
        st.session_state["applications"] = result if isinstance(result, list) else []

    applications = st.session_state.get("applications", [])
    if not applications:
        st.info("No applications loaded yet.")
        return

    st.dataframe(applications, use_container_width=True, hide_index=True)
    st.divider()
    for app in applications[:20]:
        app_id = app.get("id")
        with st.expander(f"{app.get('state', 'UNKNOWN')} application {app_id}"):
            st.write(app)
            col1, col2, col3 = st.columns([0.25, 0.25, 0.5])
            with col1:
                next_stage = st.selectbox("Move to", APPLICATION_STAGES, key=f"stage_{app_id}")
            with col2:
                if st.button("Update stage", key=f"update_{app_id}"):
                    payload = {"stage": next_stage, "note": "Updated from Streamlit dashboard"}
                    result, error, _ = request_api("PATCH", f"{API_PREFIX}/applications/{app_id}/stage", json=payload)
                    if error:
                        st.error(error)
                    else:
                        st.success("Stage updated")
                        st.json(result)
            with col3:
                if st.button("Generate email", key=f"email_{app_id}"):
                    result, error, _ = request_api(
                        "POST",
                        f"{API_PREFIX}/email/generate",
                        json={"application_id": app_id},
                    )
                    if error:
                        st.error(error)
                    else:
                        st.success("Email generation queued")
                        st.json(result)


@st.cache_data(show_spinner=False)
def scan_repo() -> dict[str, Any]:
    files: list[dict[str, Any]] = []
    for path in PROJECT_ROOT.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(PROJECT_ROOT)
        parts = set(rel.parts)
        if parts & EXCLUDED_DIRS:
            continue
        if path.suffix.lower() in EXCLUDED_SUFFIXES:
            continue
        try:
            size = path.stat().st_size
        except OSError:
            continue
        files.append(
            {
                "path": rel.as_posix(),
                "suffix": path.suffix.lower() or "[none]",
                "size": size,
                "is_text": is_text_file(path),
            }
        )

    counts = Counter(file["suffix"] for file in files)
    largest = sorted(files, key=lambda item: item["size"], reverse=True)[:12]
    tree = build_tree_preview([file["path"] for file in files])
    notes = infer_architecture(files)
    return {"files": files, "counts": counts, "largest": largest, "tree": tree, "notes": notes}


def is_text_file(path: Path) -> bool:
    if path.name.startswith(".env"):
        return False
    if path.suffix.lower() in TEXT_SUFFIXES:
        return True
    try:
        sample = path.read_bytes()[:1024]
    except OSError:
        return False
    return b"\x00" not in sample


def build_tree_preview(paths: list[str], max_lines: int = 90) -> str:
    lines: list[str] = []
    seen_dirs: set[str] = set()
    for rel_path in sorted(paths):
        parts = rel_path.split("/")
        for depth, part in enumerate(parts[:-1]):
            directory = "/".join(parts[: depth + 1])
            if directory not in seen_dirs:
                seen_dirs.add(directory)
                lines.append(f"{'  ' * depth}{part}/")
        lines.append(f"{'  ' * (len(parts) - 1)}{parts[-1]}")
        if len(lines) >= max_lines:
            lines.append("...")
            break
    return "\n".join(lines)


def infer_architecture(files: list[dict[str, Any]]) -> list[str]:
    paths = {file["path"] for file in files}
    notes: list[str] = []
    if "app/main.py" in paths:
        notes.append("FastAPI application entrypoint detected at app/main.py.")
    if "ui/streamlit_app.py" in paths:
        notes.append("Streamlit dashboard detected under ui/.")
    if any(path.startswith("app/tasks/") for path in paths):
        notes.append("Celery task modules detected under app/tasks/.")
    if any(path.startswith("app/agents/") for path in paths):
        notes.append("Agent graph and node modules detected under app/agents/.")
    if any(path.startswith("alembic/") for path in paths):
        notes.append("Alembic migrations detected for database schema management.")
    if "docker-compose.yml" in paths:
        notes.append("Docker Compose stack detected for local services.")
    return notes or ["No common architecture markers detected."]


def read_selected_files(paths: list[str], max_file_chars: int = 12_000, max_total_chars: int = 45_000) -> str:
    chunks: list[str] = []
    total = 0
    for rel_path in paths:
        path = (PROJECT_ROOT / rel_path).resolve()
        if PROJECT_ROOT not in path.parents and path != PROJECT_ROOT:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            chunks.append(f"\n--- {rel_path} ---\n[Could not read file: {exc}]")
            continue
        text = text[:max_file_chars]
        block = f"\n--- {rel_path} ---\n{text}"
        remaining = max_total_chars - total
        if remaining <= 0:
            break
        chunks.append(block[:remaining])
        total += len(block[:remaining])
    return "\n".join(chunks)


def run_llm_analysis(mode: str, context: str, question: str | None = None) -> str:
    from app.llm import get_llm_client

    system_prompt = (
        "You are a senior software engineer analyzing a local repository. "
        "Be concrete, cite file paths from the provided context, and avoid inventing files."
    )
    if mode == "Summarize selected files":
        prompt = f"Summarize these selected repository files and explain their responsibilities:\n{context}"
    elif mode == "Explain architecture":
        prompt = f"Explain the architecture, data flow, and important runtime dependencies from this repository context:\n{context}"
    else:
        prompt = f"Question: {question or 'Explain this repository.'}\n\nRepository context:\n{context}"
    return get_llm_client().retry_with_fallback(prompt=prompt, system_prompt=system_prompt)


def render_folder_analyzer_tab() -> None:
    st.subheader("Folder Analyzer")
    scan = scan_repo()
    files = scan["files"]

    metric1, metric2, metric3 = st.columns(3)
    metric1.metric("Files scanned", len(files))
    metric2.metric("Text files", sum(1 for file in files if file["is_text"]))
    metric3.metric("Project root", PROJECT_ROOT.name)

    left, right = st.columns([0.45, 0.55])
    with left:
        st.caption("Tree preview")
        st.code(scan["tree"], language="text")
    with right:
        st.caption("Architecture notes")
        for note in scan["notes"]:
            st.write(f"- {note}")
        st.caption("File counts")
        st.dataframe(
            [{"extension": ext, "count": count} for ext, count in scan["counts"].most_common()],
            use_container_width=True,
            hide_index=True,
        )

    st.caption("Largest scanned files")
    st.dataframe(scan["largest"], use_container_width=True, hide_index=True)

    text_files = [file["path"] for file in files if file["is_text"]]
    default_selection = [
        path
        for path in [
            "README.md",
            "app/main.py",
            "app/api/v1/router.py",
            "app/api/v1/search.py",
            "app/api/v1/jobs.py",
            "ui/streamlit_app.py",
        ]
        if path in text_files
    ]
    selected = st.multiselect(
        "Files to include in LLM context",
        text_files,
        default=default_selection,
        max_selections=12,
    )
    mode = st.radio(
        "Analysis mode",
        ["Summarize selected files", "Explain architecture", "Ask a question"],
        horizontal=True,
    )
    question = ""
    if mode == "Ask a question":
        question = st.text_area("Question", placeholder="What does this app do and where should I add a new endpoint?")

    with st.expander("Selected context preview"):
        preview = read_selected_files(selected, max_file_chars=4_000, max_total_chars=16_000)
        st.code(preview or "No files selected.", language="text")

    if st.button("Run analysis", disabled=not selected):
        context = read_selected_files(selected)
        if not context.strip():
            st.error("No readable context selected.")
            return
        with st.spinner("Asking the configured model..."):
            try:
                answer = run_llm_analysis(mode, context, question)
            except Exception as exc:
                st.error(f"LLM analysis failed: {exc}")
                return
        st.markdown(answer)


def main() -> None:
    render_header()
    render_auth_panel()

    tabs = st.tabs(["Discover", "Tasks", "Jobs", "Applications", "Folder Analyzer"])
    with tabs[0]:
        render_discover_tab()
    with tabs[1]:
        render_tasks_tab()
    with tabs[2]:
        render_jobs_tab()
    with tabs[3]:
        render_applications_tab()
    with tabs[4]:
        render_folder_analyzer_tab()


if __name__ == "__main__":
    main()
