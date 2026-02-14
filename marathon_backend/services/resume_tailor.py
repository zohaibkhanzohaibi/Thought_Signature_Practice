"""
Resume Tailor Service - Analyzes JD and generates tailored resume using Gemini Pro.
Combines: Recruiter Agent (analysis) + Writer Agent (drafting) + Critic Agent (review loop)
"""
import json
import re
from typing import Dict, Tuple, Optional, Union
from dotenv import load_dotenv
from .gemini_client import call_gemini

load_dotenv()

# ============================================
# HELPER - Bulletproof JSON Extraction
# ============================================

def extract_json(text: str) -> Dict:
    """
    Aggressively hunts for JSON objects in a string, ignoring markdown,
    conversation, and formatting errors.
    """
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    start = text.find('{')
    end = text.rfind('}')
    
    if start == -1 or end == -1:
        pattern = r"```(?:json)?\s*(.*?)\s*```"
        match = re.search(pattern, text, re.DOTALL)
        if match:
            text = match.group(1)
            start = text.find('{')
            end = text.rfind('}')
    
    if start != -1 and end != -1:
        json_str = text[start:end+1]
    else:
        raise ValueError("No JSON braces found in response")

    try:
        json_str = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', json_str)
        json_str = re.sub(r",\s*}", "}", json_str)
        json_str = re.sub(r",\s*]", "]", json_str)
        return json.loads(json_str, strict=False)
    except json.JSONDecodeError:
        try:
             json_str = json_str.replace('\n', '\\n').replace('\r', '').replace('\t', '\\t')
             return json.loads(json_str, strict=False)
        except:
            print(f"❌ Unfixable JSON: {json_str[:500]}...")
            raise ValueError("Fatal JSON parsing error")


# ============================================
# RECRUITER AGENT - Analyze Job Description
# ============================================

async def analyze_job_description(jd_text: str) -> Dict:
    """Analyze a Job Description to extract requirements."""
    prompt = f"""You are an expert Technical Recruiter. Analyze this Job Description.

Extract the following into structured JSON:
1. "company_name": Name or "Hiring Manager"
2. "job_title": Role title
3. "hard_skills": List of technical skills
4. "soft_skills": List of soft skills
5. "experience_level": junior/mid/senior

--- JOB DESCRIPTION ---
{jd_text}

Return ONLY raw JSON.
"""
    try:
        text = call_gemini(prompt, max_tokens=2048, temperature=0.1)
        return extract_json(text)
    except Exception as e:
        print(f"❌ JD Analysis failed: {e}")
        return {
            "company_name": "Hiring Company",
            "job_title": "Applicant",
            "hard_skills": ["Python", "Communication"],
            "soft_skills": [],
            "experience_level": "mid"
        }


# ============================================
# WRITER AGENT - Draft Tailored Resume
# ============================================

async def draft_resume(
    profile_data: Dict,
    portfolio_data: Dict,
    jd_analysis: Dict,
    feedback: str = ""
) -> Optional[Dict]:
    """Draft a tailored resume in JSON format."""
    
    if "JSON Parsing failed" in feedback or "Review error" in feedback:
        feedback = "Ensure the output is valid JSON format."

    system_prompt = """You are an expert Resume Writer.
Tailor the profile to the JD.

RULES:
1. Use the STAR method for bullets.
2. IMPORTANT: You MUST return valid JSON. Do NOT use markdown formatting.
3. Do NOT include placeholders like [FULL NAME] or [PHONE]. Use data from the candidate profile.
4. If data is missing (e.g. phone number), use empty string "" or omit the field.
5. Do not invent experiences, but highlight relevant existing ones.

OUTPUT STRUCTURE:
{
  "personal_info": { "name": "...", "email": "...", "phone": "...", "linkedin_url": "...", "github_url": "..." },
  "experience": [{ "company": "...", "role": "...", "dates": "...", "location": "...", "bullets": ["..."] }],
  "education": [{ "school": "...", "degree": "...", "dates": "...", "location": "..." }],
  "projects": [{ "name": "...", "tech_stack": "...", "dates": "...", "bullets": ["..."] }],
  "skills": [{ "category": "...", "values": "..." }]
}
"""

    candidate_json = profile_data.get('parsed_resume') or profile_data
    
    user_prompt = f"""
--- CANDIDATE ---
{json.dumps(candidate_json, indent=2)}

--- TARGET JOB ---
{json.dumps(jd_analysis, indent=2)}

--- CRITIC FEEDBACK (Implement these fixes) ---
{feedback if feedback else "None. First draft."}
"""

    try:
        text = call_gemini(user_prompt, system=system_prompt, max_tokens=8192, temperature=0.4)
        return extract_json(text)
    except Exception as e:
        print(f"❌ Resume drafting failed: {e}")
        return None


# ============================================
# CRITIC AGENT - Review and Score Resume
# ============================================

async def review_resume(resume_json: Dict, jd_text: str) -> Tuple[int, str]:
    """Review draft resume against JD."""
    prompt = f"""You are a Technical Hiring Manager.
Compare the Resume JSON to the Job Description.

Return JSON ONLY:
{{
    "score": <integer 0-100>,
    "critique": "<text>",
    "missing_keywords": ["<text>"]
}}

--- RESUME ---
{json.dumps(resume_json, indent=2)}

--- JD ---
{jd_text[:1000]}... (truncated)
"""

    try:
        text = call_gemini(prompt, max_tokens=1024, temperature=0.1)
        review = extract_json(text)
        return review.get("score", 70), review.get("critique", "Good match.")
    except Exception as e:
        print(f"❌ Resume review failed: {e}")
        return 80, "Review system timeout. Proceeding with current draft."


# ============================================
# FULL TAILORING PIPELINE
# ============================================

async def tailor_resume_for_job(
    profile: Union[Dict, str],
    portfolio: Dict,
    job_description: str,
    max_iterations: int,
    quality_threshold: int
) -> Tuple[Dict, Dict, int]:
    """
    Full pipeline with 'Best Draft' tracking.
    """
    # Robustness Fix: Handle if profile is passed as a raw string
    if isinstance(profile, str):
        # Wrap it so agents can handle it
        profile = {"parsed_resume": profile}

    print("🕵️ Analyzing job description...")
    jd_analysis = await analyze_job_description(job_description)
    
    current_draft = None
    feedback = ""
    
    # TRACKING BEST RESULT
    best_draft = None
    best_score = -1

    # Initialize best_draft with parsed resume as fallback
    if isinstance(profile, dict) and profile.get('parsed_resume'):
        best_draft = profile.get('parsed_resume')

    for iteration in range(max_iterations):
        print(f"✍️ Drafting resume (iteration {iteration + 1}/{max_iterations})...")
        
        # Draft
        new_draft = await draft_resume(profile, portfolio, jd_analysis, feedback)
        
        if not new_draft:
            print("❌ Failed to generate draft. Using best available version.")
            break
            
        current_draft = new_draft

        # Review
        print("🧐 Reviewing draft...")
        score, critique = await review_resume(current_draft, job_description)
        
        print(f"   -> Score: {score}")

        # Update Best Draft
        if score > best_score:
            best_score = score
            best_draft = current_draft
            # Ensure specifically required fields exist
            if 'personal_info' not in best_draft: best_draft['personal_info'] = {}

        # Threshold check
        if score >= quality_threshold:
            print(f"✅ Quality threshold met.")
            break
            
        feedback = critique

    # FINAL SAFETY CHECK
    if not best_draft:
        print("⚠️ No valid draft generated. Returning raw profile.")
        best_draft = profile.get('parsed_resume', {}) if isinstance(profile, dict) else {}
        
    return jd_analysis, best_draft, best_score


# ============================================
# COVER EMAIL GENERATION
# ============================================

async def generate_cover_email(tailored_resume: Dict, jd_analysis: Dict, profile: Dict) -> str:
    """Generate email."""
    # 1. Extract Details from the Tailored Resume (Preferred source)
    personal = tailored_resume.get('personal_info', {})
    
    # 2. Fallback to Profile data if Resume is empty
    candidate_name = personal.get('name') or profile.get('full_name') or "Candidate"
    candidate_email = personal.get('email') or profile.get('email') or ""
    candidate_phone = personal.get('phone') or profile.get('phone') or ""
    
    job_title = jd_analysis.get('job_title', 'the role')
    company = jd_analysis.get('company_name', 'your company')
    
    try:
        prompt = f"""
        Write a professional, concise, and enthusiastic job application email.
        
        CONTEXT:
        - Role: {job_title}
        - Company: {company}
        - Candidate Name: {candidate_name}
        - Candidate Email: {candidate_email}
        - Candidate Phone: {candidate_phone}
        - Highlights: {len(tailored_resume.get('experience', []))} years of relevant experience.

        INSTRUCTIONS:
        1. Keep it short (under 200 words).
        2. Highlight specific technical skills mentioned in the resume.
        3. STRICT REQUIREMENT: Sign off using the Candidate Name provided above. 
        4. DO NOT use placeholders like "[Your Name]" or "[Phone Number]". If data is missing, just omit that line.
        5. Include a professional Subject line at the very top.
        """
        return call_gemini(prompt, max_tokens=1024, temperature=0.7)
    except Exception as e:
        print(f"Email generation error: {e}")
        return f"Subject: Application for {job_title}\n\nDear Hiring Team,\n\nI am writing to apply for the {job_title} position at {company}. Please find my resume attached.\n\nBest regards,\n\n{candidate_name}\n{candidate_email}"


# ============================================
# RESUME TAILOR SERVICE CLASS
# ============================================

class ResumeTailorService:
    """
    Service class for resume tailoring operations.
    """

    def __init__(self, profile: Dict = None, portfolio: Dict = None):
        self.profile = profile or {}
        self.portfolio = portfolio or {"projects": [], "repos": []}
        self.last_jd_analysis: Optional[Dict] = None
        self.last_tailored_resume: Optional[Dict] = None
        self.last_score: int = 0

    async def analyze_jd(self, job_description: str) -> Dict:
        return await analyze_job_description(job_description)

    async def tailor(self, job_description: str, max_iterations: int = 3, quality_threshold: int = 85):
        jd_analysis, tailored_resume, score = await tailor_resume_for_job(
            self.profile,
            self.portfolio,
            job_description,
            max_iterations,
            quality_threshold
        )
        
        self.last_jd_analysis = jd_analysis
        self.last_tailored_resume = tailored_resume
        self.last_score = score
        
        return jd_analysis, tailored_resume, score

    async def generate_email(self, jd_analysis: Dict = None, tailored_resume: Dict = None) -> str:
        jd = jd_analysis or self.last_jd_analysis or {}
        resume = tailored_resume or self.last_tailored_resume or {}
        
        return await generate_cover_email(resume, jd, self.profile)