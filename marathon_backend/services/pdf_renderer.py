"""
PDF Renderer Service - Generate PDF resumes using LaTeX.
Based on Ahmed's latex_renderer.py with Jinja2 templating.

Uses custom Jinja2 delimiters to avoid conflicts with LaTeX:
- \\BLOCK{} for control structures (for, if, etc.)
- \\VAR{} for variable interpolation
"""
import os
import re
import subprocess
import shutil
from pathlib import Path
from typing import Dict, Optional

import jinja2

# --- CONFIGURATION ---
TEMPLATE_DIR = Path(__file__).parent.parent / "templates"
OUTPUT_DIR = Path(__file__).parent.parent / "output"

# Ensure directories exist
TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def escape_latex_chars(text: str) -> str:
    """
    Escapes special LaTeX characters in a string to prevent compilation errors.
    Example: "C++ & Python" -> "C++ \\& Python"
    """
    if not isinstance(text, str):
        return text
    
    # Map of special chars to their escaped versions
    conv = {
        '&': r'\&',
        '%': r'\%',
        '$': r'\$',
        '#': r'\#',
        '_': r'\_',
        '{': r'\{',
        '}': r'\}',
        '~': r'\textasciitilde{}',
        '^': r'\^{}',
        '\\': r'\textbackslash{}',
        '<': r'\textless{}',
        '>': r'\textgreater{}',
    }
    
    # Create a regex that matches any of the special characters
    regex = re.compile('|'.join(
        re.escape(str(key)) for key in sorted(conv.keys(), key=lambda item: -len(item))
    ))
    
    # Replace matches with their escaped counterparts
    return regex.sub(lambda match: conv[match.group()], text)


def escape_data(data) -> any:
    """
    Recursively traverses a JSON object (dict/list) and escapes all string values.
    """
    if isinstance(data, dict):
        return {k: escape_data(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [escape_data(i) for i in data]
    elif isinstance(data, str):
        return escape_latex_chars(data)
    return data


def check_latex_available() -> bool:
    """Check if any LaTeX compiler is installed."""
    return shutil.which("pdflatex") is not None or shutil.which("tectonic") is not None


def compile_latex(tex_path: str, output_dir: str = None) -> Optional[str]:
    """
    Compiles the .tex file into a .pdf using pdflatex (MiKTeX/TeX Live) or Tectonic.
    
    Args:
        tex_path: Path to the .tex file
        output_dir: Directory for output files (default: same as tex file)
        
    Returns:
        Path to generated PDF, or None if failed
    """
    if output_dir is None:
        output_dir = str(OUTPUT_DIR)
    
    # 1. Try pdflatex (Standard LaTeX compiler)
    if shutil.which("pdflatex"):
        print(f"   ⚙️  Compiling with pdflatex...")
        cmd = [
            "pdflatex", 
            "-interaction=nonstopmode", 
            "-output-directory", output_dir, 
            tex_path
        ]
        
    # 2. Fallback to Tectonic if pdflatex is missing
    elif shutil.which("tectonic"):
        print(f"   ⚙️  Compiling with Tectonic (Fallback)...")
        cmd = ["tectonic", "-o", output_dir, tex_path]
        
    else:
        print("   ❌ Error: No LaTeX compiler found. Please install 'MiKTeX' or 'TeX Live'.")
        print("   💡 On Windows: choco install miktex")
        print("   💡 On macOS: brew install --cask mactex")
        print("   💡 On Linux: sudo apt install texlive-full")
        return None

    try:
        # Run the compilation (run twice for proper references)
        for _ in range(2):
            result = subprocess.run(
                cmd, 
                check=True, 
                stdout=subprocess.DEVNULL, 
                stderr=subprocess.PIPE,
                timeout=60
            )
        
        pdf_name = Path(tex_path).stem + ".pdf"
        pdf_path = os.path.join(output_dir, pdf_name)
        
        if os.path.exists(pdf_path):
            return pdf_path
        return None
        
    except subprocess.CalledProcessError as e:
        print(f"   ❌ Compilation Failed!")
        print("\n--- LATEX ERROR LOG ---")
        try:
            print(e.stderr.decode())
        except:
            print(e.stderr)
        print("-----------------------")
        return None
    except subprocess.TimeoutExpired:
        print("   ❌ LaTeX compilation timed out")
        return None


def render_pdf(resume_json: Dict, output_name: str = "tailored_resume") -> Optional[str]:
    """
    Main function to generate the PDF from resume JSON.
    
    Args:
        resume_json (dict): The AI-generated resume content with structure:
            - personal_info: {name, phone, email, linkedin_url, github_url}
            - education: [{school, location, degree, dates}]
            - experience: [{company, location, role, dates, bullets: []}]
            - projects: [{name, tech_stack, dates, bullets: []}]
            - skills: [{category, values}]
        output_name (str): Filename without extension
        
    Returns:
        str: Path to the generated PDF, or None if failed
    """
    print("🖨️ [Renderer] Generating PDF...")
    
    # 1. Check template exists
    template_path = TEMPLATE_DIR / "resume.tex"
    if not template_path.exists():
        print(f"   ❌ Template 'resume.tex' not found in {TEMPLATE_DIR}")
        return None
    
    # 2. Sanitize Data (Crucial Step - escape LaTeX special chars)
    clean_data = escape_data(resume_json)
    
    # 3. Ensure required keys exist with defaults
    clean_data.setdefault('personal_info', {
        'name': 'Name',
        'phone': '',
        'email': '',
        'linkedin_url': '',
        'github_url': ''
    })
    clean_data.setdefault('education', [])
    clean_data.setdefault('experience', [])
    clean_data.setdefault('projects', [])
    clean_data.setdefault('skills', [])
    
    # 4. Setup Jinja2 Environment for LaTeX
    # Custom delimiters to avoid conflict with LaTeX syntax
    latex_jinja_env = jinja2.Environment(
        block_start_string=r'\BLOCK{',
        block_end_string='}',
        variable_start_string=r'\VAR{',
        variable_end_string='}',
        comment_start_string=r'\#{',
        comment_end_string='}',
        line_statement_prefix=None,
        line_comment_prefix='%#',
        trim_blocks=True,
        autoescape=False,
        loader=jinja2.FileSystemLoader(str(TEMPLATE_DIR))
    )

    # 5. Render Template
    try:
        template = latex_jinja_env.get_template('resume.tex')
        rendered_tex = template.render(**clean_data)
    except jinja2.TemplateNotFound:
        print(f"   ❌ Template 'resume.tex' not found in {TEMPLATE_DIR}")
        return None
    except jinja2.TemplateError as e:
        print(f"   ❌ Jinja2 Template Error: {e}")
        return None

    # 6. Save .tex File
    tex_path = OUTPUT_DIR / f"{output_name}.tex"
    with open(tex_path, "w", encoding="utf-8") as f:
        f.write(rendered_tex)
    print(f"   📄 LaTeX source saved: {tex_path}")
    
    # 7. Compile to PDF
    pdf_path = compile_latex(str(tex_path), str(OUTPUT_DIR))
    
    if pdf_path:
        print(f"✅ [Renderer] PDF saved: {pdf_path}")
        # Clean up auxiliary files
        cleanup_latex_aux(OUTPUT_DIR, output_name)
    else:
        print(f"   ⚠️ PDF compilation failed. LaTeX source available at: {tex_path}")
    
    return pdf_path


def cleanup_latex_aux(output_dir: Path, basename: str):
    """Remove LaTeX auxiliary files after compilation."""
    aux_extensions = ['.aux', '.log', '.out', '.fls', '.fdb_latexmk', '.synctex.gz']
    for ext in aux_extensions:
        aux_file = output_dir / f"{basename}{ext}"
        if aux_file.exists():
            try:
                aux_file.unlink()
            except:
                pass


def generate_resume_pdf(
    data: Dict,
    output_path: str = None,
    output_name: str = None
) -> Optional[str]:
    """
    High-level function to generate PDF resume.
    
    Args:
        data: Resume data dictionary
        output_path: Full path for output (optional, overrides output_name)
        output_name: Just the filename without extension
        
    Returns:
        Path to generated PDF or None
    """
    if output_path:
        output_name = Path(output_path).stem
        # Ensure output directory exists
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    if not output_name:
        from datetime import datetime
        output_name = f"resume_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    pdf_path = render_pdf(data, output_name)
    
    # If custom output_path specified, move the file
    if pdf_path and output_path:
        try:
            shutil.move(pdf_path, output_path)
            return output_path
        except:
            return pdf_path
    
    return pdf_path


def convert_tailored_to_pdf_data(tailored_resume: Dict, profile: Dict) -> Dict:
    """
    Convert tailored resume from writer agent to PDF data format.
    
    Args:
        tailored_resume: Output from resume_tailor.tailor_resume_for_job()
        profile: User profile with base info
        
    Returns:
        Dict ready for generate_resume_pdf()
    """
    # If tailored_resume is already in correct format
    if "personal_info" in tailored_resume:
        return tailored_resume
    
    # Convert from flat format
    return {
        "personal_info": {
            "name": profile.get("full_name", tailored_resume.get("name", "")),
            "email": profile.get("email", tailored_resume.get("email", "")),
            "phone": profile.get("phone", tailored_resume.get("phone", "")),
            "linkedin_url": profile.get("linkedin_url", tailored_resume.get("linkedin", "")),
            "github_url": profile.get("github_url", tailored_resume.get("github", ""))
        },
        "education": tailored_resume.get("education", []),
        "experience": tailored_resume.get("experience", []),
        "projects": tailored_resume.get("projects", []),
        "skills": tailored_resume.get("skills", [])
    }


# --- TEST BLOCK ---
if __name__ == "__main__":
    # Dummy data to test the renderer
    test_data = {
        "personal_info": {
            "name": "Jane Doe",
            "phone": "555-0199",
            "email": "jane@example.com",
            "linkedin_url": "linkedin.com/in/jane",
            "github_url": "github.com/jane"
        },
        "education": [
            {
                "school": "Tech University", 
                "location": "New York, NY", 
                "degree": "B.S. Computer Science", 
                "dates": "2020-2024"
            }
        ],
        "experience": [
            {
                "company": "Startup Inc", 
                "location": "Remote", 
                "role": "Software Developer", 
                "dates": "2023-Present",
                "bullets": [
                    "Fixed critical bug in C++ & Python code reducing crashes by 50%",
                    "Managed deployment pipeline for 150+ daily releases"
                ]
            }
        ],
        "projects": [
            {
                "name": "AI Job Agent",
                "tech_stack": "Python, FastAPI, LangChain",
                "bullets": [
                    "Built automated job search agent with 85% accuracy",
                    "Integrated with Gmail API for draft creation"
                ]
            }
        ],
        "skills": [
            {"category": "Languages", "values": "Python, C++, JavaScript"},
            {"category": "Frameworks", "values": "FastAPI, React, Docker"}
        ]
    }
    
    # Run test
    if check_latex_available():
        result = render_pdf(test_data, "test_resume")
        if result:
            print(f"\n🎉 Test successful! PDF at: {result}")
    else:
        print("⚠️ LaTeX not installed. Install MiKTeX or TeX Live to generate PDFs.")
