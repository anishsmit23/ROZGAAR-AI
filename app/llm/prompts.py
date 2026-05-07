"""
Prompt templates for all agent nodes.
Organized by agent workflow.
"""

# ============================================================================
# JOB SEARCH AGENT PROMPTS
# ============================================================================

NORMALIZE_JOB_DESCRIPTION = """You are a job description analyzer. Extract and normalize the following job posting into structured JSON format.

Job Description:
{job_description}

Extract the following information (use None for missing values):
- job_title (str)
- company (str)
- location (str)
- seniority_level (junior|mid|senior|lead|exec)
- employment_type (full-time|part-time|contract|freelance)
- salary_min (int, nullable)
- salary_max (int, nullable)
- currency (str, e.g., USD, INR)
- job_type (job_type_value)
- key_skills (list of str, top 5-10)
- responsibilities (list of str, top 3-5)
- qualifications (list of str, top 3-5)
- benefits (list of str)
- remote_type (remote|hybrid|onsite)
- posting_date (str, ISO format if available)

Return ONLY valid JSON with no markdown formatting or code blocks."""

RANK_JOBS_BY_FIT = """You are a career advisor. Given a user's resume and a list of job postings, rank them by fit (1-10 score).

User Resume Summary:
{resume_summary}

Available Jobs:
{jobs_list}

For each job, provide:
- job_id (str)
- match_score (1-10)
- top_3_match_reasons (list of str)
- top_3_gaps (list of str)

Return ONLY valid JSON array of ranked jobs."""

# ============================================================================
# RESUME TAILOR AGENT PROMPTS
# ============================================================================

RETRIEVE_RELEVANT_RESUME_SECTIONS = """You are a resume expert. Given a job description and the user's resume, identify which sections are most relevant to highlight.

Job Description:
{job_description}

Resume:
{resume}

Identify the top 3-5 resume sections that are most relevant to this job. For each section, suggest 1-2 bullet points to emphasize.

Return ONLY valid JSON:
{{
    "relevant_sections": [
        {{"section": "str", "highlighted_bullets": ["str", "str"]}}
    ]
}}"""

TAILOR_RESUME_FOR_JOB = """You are an expert resume writer. Tailor the user's resume to match the target job description while maintaining authenticity and accuracy.

Job Description:
{job_description}

Original Resume:
{resume}

Current Highlighted Sections:
{highlighted_sections}

Rewrite the resume to:
1. Emphasize skills matching the job requirements
2. Use keywords from the job description
3. Highlight relevant achievements
4. Maintain a professional tone
5. Keep the resume to max 1-2 pages

Return the ONLY the tailored resume text. Do NOT include any JSON or markdown formatting."""

EVALUATE_TAILORED_RESUME = """You are a resume evaluation expert. Evaluate how well the tailored resume matches the job description.

Job Description:
{job_description}

Tailored Resume:
{tailored_resume}

Evaluate on these criteria (1-10 for each):
- keyword_match (how well resume uses job description keywords)
- skills_alignment (how well resume skills match required skills)
- achievement_fit (how well achievements match job context)
- readability (clarity and professional presentation)

Provide:
- overall_score (avg of 4 criteria, 1-10)
- strengths (list of 2-3 str)
- improvements (list of 2-3 str, if score < 7)
- recommendation (retry|approve)

Return ONLY valid JSON."""

# ============================================================================
# EMAIL GENERATION AGENT PROMPTS
# ============================================================================

GENERATE_EMAIL_TO_RECRUITER = """You are a professional email writer. Write a compelling email to a recruiter that:
1. Introduces the candidate professionally
2. References the specific job posting
3. Highlights top 2-3 relevant achievements
4. Expresses genuine interest
5. Includes a clear call-to-action

Job Title: {job_title}
Company: {company}
Recruiter Name: {recruiter_name} (optional)

Candidate Profile:
- Name: {candidate_name}
- Key Skills: {key_skills}
- Top Achievement: {top_achievement}

Write the email now. Include:
- subject_line (str, max 60 chars)
- body (str, 150-300 words)
- tone (professional|casual|enthusiastic)

Return ONLY the email content as plain text. NO JSON."""

EVALUATE_EMAIL = """You are an email effectiveness expert. Evaluate this email to a recruiter.

Job: {job_title} at {company}
Email Subject: {email_subject}
Email Body:
{email_body}

Evaluate on (1-10 each):
- professionalism (tone, grammar, formatting)
- relevance (how well it matches job & company)
- personalization (is it specific, not generic?)
- urgency (does it encourage response?)

Provide:
- overall_score (avg of 4 criteria)
- strengths (list of 2-3 str)
- improvements (list of 2-3 str if score < 7)
- recommendation (retry|send)

Return ONLY valid JSON."""

# ============================================================================
# UTILITY PROMPTS
# ============================================================================

EXTRACT_KEY_SKILLS = """From this text, extract the top 5-10 key technical and domain skills.

Text: {text}

Return ONLY a JSON array of skill strings. Example:
["Python", "Machine Learning", "AWS", "SQL", "Docker"]"""

SUMMARIZE_ACHIEVEMENT = """Summarize this achievement in 1-2 sentences, emphasizing business impact and measurable results:

Achievement: {achievement}

Return ONLY the summary text. NO quotes or markdown."""

GENERATE_INTERVIEW_QUESTIONS = """You are an expert interviewer for the following role. Generate likely interview questions.

Job Title: {job_title}
Company: {company}
Job Description: {job_description}
Candidate Background: {candidate_background}

Generate 5-7 interview questions that:
1. Test core competencies for the role
2. Probe for specific experience
3. Assess cultural fit
4. Challenge the candidate appropriately
5. Are based on the job description

Return questions as a JSON array:
["question1", "question2", "question3", ...]"""

GENERATE_MODEL_ANSWERS = """You are a career coach. Generate a strong model answer to this interview question based on the candidate's background.

Candidate Background: {candidate_background}
Interview Question: {interview_question}

The answer should:
1. Be 2-3 minutes when read aloud (150-200 words)
2. Include specific examples (STAR method: Situation, Task, Action, Result)
3. Highlight relevant skills and achievements
4. Show problem-solving abilities
5. Be authentic and conversational

Return ONLY the model answer text. NO JSON or markdown."""
