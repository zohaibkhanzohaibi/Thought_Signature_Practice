"""
Resume Tailor Service - Analyzes JD and generates tailored resume using Gemini Pro.
Combines: Recruiter Agent (analysis) + Writer Agent (drafting) + Critic Agent (review loop)
"""
import json
from typing import Dict, Tuple, Optional
from dotenv import load_dotenv
from .gemini_client import call_gemini

load_dotenv()


# ============================================
# RECRUITER AGENT - Analyze Job Description
# ============================================

async def analyze_job_description(jd_text: str) -> Dict:
    """
    Analyze a Job Description to extract requirements and hidden signals.
    """
    prompt = f"""You are an expert Technical Recruiter. Analyze this Job Description.

Extract the following into structured JSON:
1. "company_name": The hiring company name (or "Hiring Manager" if not found)
2. "job_title": The specific role title
3. "hard_skills": List of must-have technical skills (Python, AWS, React, etc.)
4. "soft_skills": List of interpersonal skills (Leadership, Communication, etc.)
5. "culture_keywords": Words defining company culture (fast-paced, innovative, etc.)
6. "hidden_signals": What they want but didn't explicitly say
7. "company_email": Recruiter/HR email if mentioned (null if not found)
8. "experience_level": junior/mid/senior based on requirements

--- JOB DESCRIPTION ---
{jd_text}

Return ONLY raw JSON, no markdown:
{{
    "company_name": "...",
    "job_title": "...",
    "hard_skills": ["Skill1", "Skill2"],
    "soft_skills": ["Skill1", "Skill2"],
    "culture_keywords": ["Word1", "Word2"],
    "hidden_signals": ["Inference1", "Inference2"],
    "company_email": null,
    "experience_level": "mid"
}}
"""
    
    try:
        messages = [{"role": "user", "content": prompt}]
        text = call_gemini(prompt, max_tokens=2048, temperature=0.2)
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        
        return json.loads(text.strip())
    except Exception as e:
        print(f"❌ JD Analysis failed: {e}")
        return {
            "company_name": "Hiring Team",
            "job_title": "Software Engineer",
            "hard_skills": [],
            "soft_skills": [],
            "culture_keywords": [],
            "hidden_signals": [],
            "company_email": None,
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
    """
    Draft a tailored resume in JSON format based on profile and JD analysis.
    """
    system_prompt = """You are an expert Resume Strategist and Technical Writer.
Your goal is to tailor a candidate's profile to match a specific Job Description.

CRITICAL INSTRUCTIONS:
1. **EVIDENCE EXTRACTION**: Use GitHub portfolio data to prove skills
2. **EXACT NAMES**: Use EXACT spelling of company names from source
3. **STAR METHOD**: Use Situation-Task-Action-Result for bullet points
4. **QUANTIFY**: Include metrics where possible (%, users, time saved)

OUTPUT FORMAT - Return STRICTLY VALID JSON:
{
  "personal_info": { 
    "name": "...", 
    "phone": "...", 
    "email": "...", 
    "linkedin_url": "...", 
    "github_url": "..." 
  },
  "education": [{ 
    "school": "...", 
    "location": "...", 
    "degree": "...", 
    "dates": "..." 
  }],
  "experience": [{ 
    "company": "...", 
    "location": "...", 
    "role": "...", 
    "dates": "...", 
    "bullets": ["Action verb + context + result..."] 
  }],
  "projects": [{ 
    "name": "...", 
    "tech_stack": "...", 
    "dates": "...", 
    "bullets": ["..."] 
  }],
  "skills": [
    { "category": "Languages", "values": "Python, JavaScript, SQL" },
    { "category": "Frameworks", "values": "FastAPI, React, Docker" }
  ]
}
"""

    user_prompt = f"""
--- CANDIDATE PROFILE ---
Name: {profile_data.get('full_name')}
Email: {profile_data.get('email') or profile_data.get('contact_info', {}).get('email')}
Summary: {profile_data.get('summary', '')}
Skills: {', '.join(profile_data.get('skills', []))}
Experience: {profile_data.get('experience_years', 0)} years

--- PARSED RESUME DATA ---
{json.dumps(profile_data.get('parsed_resume', {}), indent=2)}

--- GITHUB PORTFOLIO ---
{json.dumps(portfolio_data, indent=2)}

--- TARGET JOB REQUIREMENTS ---
{json.dumps(jd_analysis, indent=2)}

--- PREVIOUS FEEDBACK ---
{feedback if feedback else "None. This is the first draft."}

TASK:
1. Map candidate's experience to required hard skills
2. Prioritize most relevant projects/experience first
3. Ensure skills section matches JD requirements
4. Return valid JSON only
"""

    try:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        text = call_gemini(user_prompt, system=system_prompt, max_tokens=2048, temperature=0.3)
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        
        return json.loads(text.strip())
    except Exception as e:
        print(f"❌ Resume drafting failed: {e}")
        return None


# ============================================
# CRITIC AGENT - Review and Score Resume
# ============================================

async def review_resume(resume_json: Dict, jd_text: str) -> Tuple[int, str]:
    """
    Review draft resume against JD and return score + feedback.
    Returns: (score 0-100, feedback string)
    """
    prompt = f"""You are a strict Technical Hiring Manager.
Review this resume against the Job Description.

CRITERIA:
1. Keyword Match: Are JD's technical skills included?
2. Evidence: Do bullets have metrics and specific tech?
3. Relevancy: Is the most relevant experience first?

--- JOB DESCRIPTION ---
{jd_text}

--- CANDIDATE RESUME (JSON) ---
{json.dumps(resume_json, indent=2)}

Return JSON:
{{
    "score": <0-100>,
    "critique": "Short paragraph on what's weak",
    "missing_keywords": ["list", "of", "missing", "terms"],
    "specific_fixes": [
        "Change X to Y",
        "Move section Z higher"
    ]
}}
"""

    try:
        messages = [{"role": "user", "content": prompt}]
        text = call_gemini(prompt, max_tokens=1024, temperature=0.1)
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        
        review = json.loads(text.strip())
        score = review.get("score", 0)
        
        feedback = f"Score: {score}/100.\n"
        feedback += f"Critique: {review.get('critique', '')}\n"
        feedback += f"Missing: {', '.join(review.get('missing_keywords', []))}\n"
        feedback += "Fixes:\n- " + "\n- ".join(review.get('specific_fixes', []))
        
        return score, feedback
    except Exception as e:
        print(f"❌ Resume review failed: {e}")
        return 100, "Review error. Proceeding."


# ============================================
# FULL TAILORING PIPELINE
# ============================================

async def tailor_resume_for_job(
    profile: Dict,
    portfolio: Dict,
    job_description: str,
        max_iterations: int,
        quality_threshold: int
) -> Tuple[Dict, Dict, int]:
    """
    Full resume tailoring pipeline with review loop.
    
    Returns: (jd_analysis, tailored_resume, final_score)
    """
    # Step 1: Analyze JD
    print("🕵️ Analyzing job description...")
    jd_analysis = await analyze_job_description(job_description)
    
    # Step 2: Draft and refine loop
    current_draft = None
    feedback = ""
    final_score = 0
    
    for iteration in range(max_iterations):
        print(f"✍️ Drafting resume (iteration {iteration + 1}/{max_iterations})...")
        current_draft = await draft_resume(profile, portfolio, jd_analysis, feedback)
        
        if not current_draft:
            print("❌ Failed to generate resume draft")
            break
        
        print("🧐 Reviewing draft...")
        score, critique = await review_resume(current_draft, job_description)
        final_score = score
        
        if score >= quality_threshold:
            print(f"✅ Quality threshold met (Score: {score})")
            break
        else:
            print(f"⚠️ Score {score} < {quality_threshold}. Refining...")
            feedback = critique
    
    return jd_analysis, current_draft, final_score


# ============================================
# COVER EMAIL GENERATION
# ============================================

async def generate_cover_email(
    tailored_resume: Dict,
    jd_analysis: Dict,
    profile: Dict
) -> str:
    """
    Generate a professional cover email for job application.
    """
    prompt = f"""Write a professional cover email for a job application.

APPLICANT:
- Name: {tailored_resume.get('personal_info', {}).get('name', profile.get('full_name'))}
- Email: {tailored_resume.get('personal_info', {}).get('email', '')}

TARGET JOB:
- Company: {jd_analysis.get('company_name')}
- Role: {jd_analysis.get('job_title')}
- Key Skills Required: {', '.join(jd_analysis.get('hard_skills', [])[:5])}

CANDIDATE HIGHLIGHTS:
- Experience: {len(tailored_resume.get('experience', []))} roles
- Top Skills: {', '.join([s.get('values', '') for s in tailored_resume.get('skills', [])[:2]])}

Write a concise 3-paragraph email:
1. Opening: Express interest and mention the specific role
2. Body: Highlight 2-3 relevant qualifications that match the JD
3. Closing: Call to action, availability for interview

IMPORTANT:
- Be professional but personable
- Keep it under 200 words
- Don't be generic - reference specific requirements from the JD
- End with a professional sign-off

Return ONLY the email text, no subject line or headers.
"""

    try:
        messages = [{"role": "user", "content": prompt}]
        return call_gemini(messages[-1]["content"], max_tokens=1024, temperature=0.7)
    except Exception as e:
        print(f"❌ Cover email generation failed: {e}")
        return f"""Dear Hiring Manager,

I am writing to express my interest in the {jd_analysis.get('job_title')} position at {jd_analysis.get('company_name')}.

With my experience in {', '.join(jd_analysis.get('hard_skills', ['software development'])[:3])}, I believe I would be a strong fit for this role.

I would welcome the opportunity to discuss how my skills align with your team's needs.

Best regards,
{profile.get('full_name')}
"""


# ============================================
# RESUME TAILOR SERVICE CLASS
# ============================================

class ResumeTailorService:

    async def tailor(self, job_description: str, max_iterations: int = 3, quality_threshold: int = 85):
        """
        Run the full tailoring pipeline for a job description.
        Args:
            job_description: Raw job description text
            max_iterations: Max review iterations
            quality_threshold: Minimum score to accept
        Returns:
            Tuple of (jd_analysis, tailored_resume, final_score)
        """
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
    """
    Service class for resume tailoring operations.
    Provides a unified interface for the complete tailoring pipeline.
    """
    
    def __init__(self, profile: Dict = None, portfolio: Dict = None):
        """Initialize with optional profile and portfolio data."""
        self.profile = profile or {}
        self.portfolio = portfolio or {"projects": [], "repos": []}
        self.last_jd_analysis: Optional[Dict] = None
        self.last_tailored_resume: Optional[Dict] = None
        self.last_score: int = 0
    
    def set_profile(self, profile: Dict):
        """Update the profile data."""
        self.profile = profile
    
    def set_portfolio(self, portfolio: Dict):
        """Update the portfolio data."""
        self.portfolio = portfolio
    
    async def analyze_jd(self, job_description: str) -> Dict:
        """
        Analyze a job description.
        
        Args:
            job_description: Raw job description text
            
        try:
            return call_gemini(prompt, max_tokens=512, temperature=0.7)
        except Exception as e:
            print(f"❌ Cover email generation failed: {e}")
            return (
                f"Dear Hiring Manager,\n\n"
                f"I am writing to express my interest in the {jd_analysis.get('job_title')} position at {jd_analysis.get('company_name')}.\n\n"
                f"With my experience in {', '.join(jd_analysis.get('hard_skills', ['software development'])[:3])}, I believe I would be a strong fit for this role.\n\n"
                "I would welcome the opportunity to discuss how my skills align with your team's needs.\n\n"
                f"Best regards,\n{{profile_name}}"
            ).replace("{profile_name}", profile.get('full_name', ''))
        Args:
            job_description: Raw job description text
            max_iterations: Max review iterations
            quality_threshold: Minimum score to accept
            
        Returns:
            Tuple of (jd_analysis, tailored_resume, final_score)
        """
        # Set defaults if not provided
        try:
            max_iterations
        except NameError:
            max_iterations = 3
        try:
            quality_threshold
        except NameError:
            quality_threshold = 85
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
        """
        Generate a cover email for the application.
        
        Args:
            jd_analysis: Optional JD analysis (uses last cached if not provided)
            tailored_resume: Optional resume (uses last cached if not provided)
            
        Returns:
            Cover email text
        """
        jd = jd_analysis or self.last_jd_analysis or {}
        resume = tailored_resume or self.last_tailored_resume or {}
        
        return await generate_cover_email(resume, jd, self.profile)
    
    def get_last_results(self) -> Dict:
        """Get the results from the last tailoring operation."""
        return {
            "jd_analysis": self.last_jd_analysis,
            "tailored_resume": self.last_tailored_resume,
            "score": self.last_score
        }
