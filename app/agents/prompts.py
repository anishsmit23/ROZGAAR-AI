"""Prompt engineering for LLM-powered agent tasks."""
from __future__ import annotations


def resume_customization_prompt(
    resume_text: str,
    job_title: str,
    company: str,
    job_description: str,
) -> tuple[str, str]:
    """
    Generate system and user prompts for resume customization via LLM.
    
    Args:
        resume_text: Current resume in plain text or Markdown format
        job_title: Target job title
        company: Company name
        job_description: Full job posting description/requirements
    
    Returns:
        Tuple of (system_prompt, user_prompt)
    """
    system_prompt = """You are an expert resume writer and ATS specialist. Your task is to customize resumes for specific job postings while maintaining accuracy and truthfulness.

When customizing a resume:
1. **Relevance**: Emphasize skills, experiences, and accomplishments that directly match the job requirements
2. **Keywords**: Naturally incorporate keywords from the job description (for ATS optimization)
3. **Accuracy**: Never invent or exaggerate experience. Keep all facts truthful and verifiable.
4. **Format**: Structure output in clean Markdown with standard sections: Summary, Experience, Skills, Education
5. **Optimization**: Use action verbs and quantifiable achievements; reorganize bullet points by relevance to the job
6. **Brevity**: Keep each section concise but impactful; prioritize relevance over length

Output ONLY the customized resume in Markdown format. Do not include explanations or commentary."""

    user_prompt = f"""Customize the following resume for this job opportunity:

**Job Title**: {job_title}
**Company**: {company}

**Job Description**:
{job_description}

---

**Current Resume**:
{resume_text}

---

Please rewrite the resume to highlight the most relevant skills and experiences for this {job_title} position at {company}. Ensure:
- The resume emphasizes technical skills and achievements matching the job description
- Keywords from the job posting are naturally woven in
- All information remains accurate and truthful
- The output is in clean Markdown format with sections: Summary, Experience, Skills, Education
- The resume is optimized for ATS scanning

Provide only the customized resume in Markdown format."""

    return system_prompt, user_prompt


def cold_email_prompt(
    user_name: str,
    user_skills: list[str],
    experience_years: int,
    job_title: str,
    company: str,
    job_description: str,
) -> str:
    """Build a single prompt for cold email generation."""
    skills_text = ", ".join(user_skills) if user_skills else "your core professional skills"

    return f"""You are writing a concise, high-conversion cold email for a job application.

Requirements:
- Output must start with a subject line on the first line exactly in the format: Subject: ...
- Leave one blank line after the subject line.
- Write the email body in professional Markdown/plain text.
- Keep the body between 150 and 200 words maximum.
- Be specific to the job, company, and responsibilities in the job description.
- Reference exactly one concrete skill, project, or achievement from the candidate profile.
- Use ATS-friendly and recruiter-friendly language naturally.
- End with a clear call to action.
- Do NOT use generic phrases like "I am writing to express my interest" or similar boilerplate.
- Do NOT invent experience, credentials, or projects.

Candidate profile:
- Name: {user_name}
- Years of experience: {experience_years}
- Skills: {skills_text}

Target role:
- Job title: {job_title}
- Company: {company}

Job description:
{job_description}

Write the email now. Return only the subject line and body in the required format."""
