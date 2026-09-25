"""
Native WSGI Application for Algorithmic CV Optimizer (cPanel / Phusion Passenger / LiteSpeed).

Provides 100% synchronous native WSGI compatibility without ASGI thread conversion,
eliminating event loop deadlocks in CloudLinux / LiteSpeed Passenger environments.
"""

import os
import re
import json
import uuid
import shutil
import hmac
import hashlib
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, List

from dotenv import load_dotenv
from flask import Flask, request, jsonify, render_template, send_from_directory, abort

from pipeline import run_cv_optimization_pipeline
from extractor import extract_text_from_file
from renderer import build_ats_friendly_docx, build_cover_letter_docx
from schemas import TailoredResumeSchema, ContactInformation, CoverLetterSchema
from optimizer import (
    get_openai_client,
    safe_execute_with_retry,
    DEFAULT_MODEL,
    heuristic_parse_resume,
    parse_job_description,
    extract_structured_job_model,
    heuristic_generate_evidence_map,
    mock_optimize_pipeline,
)
from section_engine import (
    recommend_sections_for_candidate,
    audit_information_loss,
    calculate_cv_quality_score,
)
from mock_stress_data import get_29_section_stress_cv_payload
from app import build_tailored_cover_letter_data, generate_heuristic_assistant_reply

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

UPLOADS_DIR = BASE_DIR / "uploads"
OUTPUTS_DIR = BASE_DIR / "outputs"
SAMPLE_DATA_DIR = BASE_DIR / "sample_data"

UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

class PrefixMiddleware:
    """Strips leading subpath prefixes so the app works at both root and subdirectories."""
    def __init__(self, wsgi_app, prefixes=("/cv_studio", "/cv_optimizer")):
        self.wsgi_app = wsgi_app
        self.prefixes = prefixes

    def __call__(self, environ, start_response):
        path = environ.get('PATH_INFO', '')
        for prefix in self.prefixes:
            if path == prefix:
                environ['PATH_INFO'] = '/'
                break
            elif path.startswith(prefix + '/'):
                environ['PATH_INFO'] = path[len(prefix):]
                break
        return self.wsgi_app(environ, start_response)


app = Flask(
    __name__,
    template_folder=str(BASE_DIR / "templates"),
    static_folder=str(BASE_DIR / "static"),
    static_url_path="/static"
)
app.wsgi_app = PrefixMiddleware(app.wsgi_app)


# Also support subdomain subpaths (e.g., /cv_studio/static/, /cv_optimizer/static/)
@app.route("/cv_studio/static/<path:filename>")
@app.route("/cv_optimizer/static/<path:filename>")
def serve_cv_optimizer_static(filename):
    return send_from_directory(str(BASE_DIR / "static"), filename)


@app.route("/", methods=["GET"])
@app.route("/cv_studio/", methods=["GET"])
@app.route("/cv_studio", methods=["GET"])
@app.route("/cv_optimizer/", methods=["GET"])
@app.route("/cv_optimizer", methods=["GET"])
def serve_index():
    """Renders the main CV optimization studio dashboard."""
    return render_template("index.html")


@app.route("/api/health", methods=["GET"])
@app.route("/cv_studio/api/health", methods=["GET"])
@app.route("/cv_optimizer/api/health", methods=["GET"])
def health_check():
    """Service health and environment status."""
    return jsonify({
        "status": "healthy",
        "has_openai_key": bool(os.environ.get("OPENAI_API_KEY")),
        "model": DEFAULT_MODEL,
        "engine": "wsgi-native"
    })


@app.route("/api/webhook", methods=["GET", "POST"])
@app.route("/cv_studio/api/webhook", methods=["GET", "POST"])
def cpanel_git_webhook():
    """Webhook endpoint for GitHub to trigger git pull and restart passenger."""
    if request.method == "GET":
        return jsonify({
            "status": "ready",
            "message": "Git Webhook listener is active. Send a POST request to trigger deployment."
        })

    secret = os.environ.get("DEPLOY_SECRET")
    if secret:
        provided_secret = request.args.get("secret") or request.headers.get("X-Deploy-Secret")
        sig_header = request.headers.get("X-Hub-Signature-256")
        valid = False
        if provided_secret and hmac.compare_digest(provided_secret, secret):
            valid = True
        elif sig_header and sig_header.startswith("sha256="):
            computed = "sha256=" + hmac.new(secret.encode(), request.data, hashlib.sha256).hexdigest()
            if hmac.compare_digest(computed, sig_header):
                valid = True
        if not valid:
            return jsonify({"error": "Unauthorized: Invalid or missing secret"}), 403

    try:
        result = subprocess.run(
            ["git", "pull", "origin", "main"],
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True,
            timeout=120
        )
        restart_dir = BASE_DIR / "tmp"
        restart_dir.mkdir(parents=True, exist_ok=True)
        (restart_dir / "restart.txt").touch()

        return jsonify({
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "message": "Deployed and restarted successfully" if result.returncode == 0 else "Git pull failed"
        }), (200 if result.returncode == 0 else 500)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/sample-data", methods=["GET"])
@app.route("/cv_studio/api/sample-data", methods=["GET"])
@app.route("/cv_optimizer/api/sample-data", methods=["GET"])
def get_sample_data():
    sample_jd_reqs = {
        "job_title": "Lead Backend Platform Engineer",
        "company_name": "Tech Solutions Ltd.",
        "required_skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "Kubernetes", "AWS"],
        "preferred_skills": ["Microservices", "CI/CD", "Redis", "Distributed Systems"]
    }
    return jsonify({
        "success": True,
        "candidate_name": "Sila Kipng'etich Tanui",
        "role_title": "Lead Backend Platform Engineer",
        "company_name": "Tech Solutions Ltd.",
        "parsed_jd": sample_jd_reqs,
        "job_requirements": sample_jd_reqs,
        "keyword_coverage": {
            "score": 0.85,
            "total_matched": 8,
            "total_required": 10,
            "matched": ["Python", "FastAPI", "Docker", "PostgreSQL", "Kubernetes", "System Architecture", "AWS", "Git"],
            "missing": ["Microservices", "CI/CD"]
        },
        "audit_report": {
            "is_valid": True,
            "discrepancies": []
        },
        "parsed_resume": {
            "contact": {
                "full_name": "Sila Kipng'etich Tanui",
                "professional_title": "Computer Scientist | Systems Software Engineer",
                "email": "silatanuikipngetich@gmail.com",
                "phone": "+36 20 323 3673",
                "location": "Debrecen, Hungary",
                "linkedin_url": "",
                "portfolio_url": ""
            },
            "summary": "Results-driven Computer Scientist and Systems Software Engineer with expertise in Python, FastAPI, Docker, and distributed systems architecture. Passionate about building scalable, high-performance backend services and automated deployment pipelines.",
            "key_achievements": [
                {"title": "High-Throughput API Platform", "description": "Architected backend services processing over 200k requests/day with 99.9% uptime using Python and FastAPI."},
                {"title": "Infrastructure Automation", "description": "Reduced deployment time by 60% by implementing Docker-based CI/CD pipelines across 4 production environments."}
            ],
            "work_experience": [
                {
                    "company": "Tech Solutions Ltd.",
                    "job_title": "Software Developer",
                    "start_date": "Jan 2022",
                    "end_date": "Present",
                    "location": "Debrecen, Hungary",
                    "bullet_points": [
                        "Architected high-throughput REST APIs using Python and FastAPI, serving 200k daily active requests with sub-50ms p99 latency.",
                        "Designed and deployed containerized microservices with Docker and Kubernetes, reducing infrastructure overhead by 40%.",
                        "Built automated CI/CD pipelines integrating GitHub Actions, Docker, and AWS ECR, cutting release cycles from 2 weeks to 3 days.",
                        "Optimized PostgreSQL query performance by introducing indexing strategies and connection pooling, improving read throughput by 3x."
                    ]
                }
            ],
            "education": [
                {
                    "institution": "University of Debrecen",
                    "degree": "B.Sc. Computer Science",
                    "field_of_study": "Computer Science",
                    "graduation_date": "2023",
                    "grade": "First Class",
                    "honors": []
                }
            ],
            "skills": ["Python", "FastAPI", "Docker", "PostgreSQL", "Kubernetes", "AWS", "Git", "System Architecture", "REST APIs", "CI/CD"],
            "skill_categories": [
                {"category_name": "Languages & Frameworks", "skills": ["Python", "FastAPI", "JavaScript", "TypeScript"]},
                {"category_name": "Infrastructure & DevOps", "skills": ["Docker", "Kubernetes", "AWS", "Git", "CI/CD"]},
                {"category_name": "Databases", "skills": ["PostgreSQL", "Redis", "MongoDB"]}
            ],
            "academic_work": [],
            "awards_and_scholarships": [],
            "languages": [
                {"language": "English", "proficiency": "C1 - Proficient"},
                {"language": "Swahili", "proficiency": "Native"}
            ],
            "certifications": [],
            "referees": "Available upon Request"
        },
        "tailored_cv": {
            "contact": {
                "full_name": "Sila Kipng'etich Tanui",
                "professional_title": "Computer Scientist | Systems Software Engineer",
                "email": "silatanuikipngetich@gmail.com",
                "phone": "+36 20 323 3673",
                "location": "Debrecen, Hungary",
                "linkedin_url": "",
                "portfolio_url": ""
            },
            "professional_summary": "Results-driven Computer Scientist and Systems Software Engineer with expertise in Python, FastAPI, Docker, and distributed systems architecture. Passionate about building scalable, high-performance backend services and automated deployment pipelines that directly solve mission-critical business problems.",
            "key_achievements": [
                {"title": "High-Throughput API Platform", "description": "Architected backend services processing over 200k requests/day with 99.9% uptime using Python and FastAPI."},
                {"title": "Infrastructure Automation", "description": "Reduced deployment time by 60% by implementing Docker-based CI/CD pipelines across 4 production environments."}
            ],
            "skills_section": ["Python", "FastAPI", "Docker", "PostgreSQL", "Kubernetes", "AWS", "Git", "System Architecture", "REST APIs", "CI/CD"],
            "skill_categories": [
                {"category_name": "Languages & Frameworks", "skills": ["Python", "FastAPI", "JavaScript", "TypeScript"]},
                {"category_name": "Infrastructure & DevOps", "skills": ["Docker", "Kubernetes", "AWS", "Git", "CI/CD"]},
                {"category_name": "Databases", "skills": ["PostgreSQL", "Redis", "MongoDB"]}
            ],
            "work_experience": [
                {
                    "company": "Tech Solutions Ltd.",
                    "job_title": "Software Developer",
                    "start_date": "Jan 2022",
                    "end_date": "Present",
                    "location": "Debrecen, Hungary",
                    "bullet_points": [
                        {"optimized_text": "Architected high-throughput REST APIs using Python and FastAPI, serving 200k daily active requests with sub-50ms p99 latency.", "original_text": "", "reasoning_steps": ""},
                        {"optimized_text": "Designed and deployed containerized microservices with Docker and Kubernetes, reducing infrastructure overhead by 40%.", "original_text": "", "reasoning_steps": ""},
                        {"optimized_text": "Built automated CI/CD pipelines integrating GitHub Actions, Docker, and AWS ECR, cutting release cycles from 2 weeks to 3 days.", "original_text": "", "reasoning_steps": ""},
                        {"optimized_text": "Optimized PostgreSQL query performance through indexing strategies and connection pooling, improving read throughput by 3x.", "original_text": "", "reasoning_steps": ""}
                    ]
                }
            ],
            "education": [
                {
                    "institution": "University of Debrecen",
                    "degree": "B.Sc. Computer Science",
                    "field_of_study": "Computer Science",
                    "graduation_date": "2023",
                    "grade": "First Class",
                    "honors": []
                }
            ],
            "academic_work": [],
            "awards_and_scholarships": [],
            "languages": [
                {"language": "English", "proficiency": "C1 - Proficient"},
                {"language": "Swahili", "proficiency": "Native"}
            ],
            "certifications": [],
            "referees": "Available upon Request",
            "custom_sections": [],
            "alignment_score_explanation": "Strong match with Systems Software Engineering requirements."
        },
        "job_model": {
            "role_title": "Lead Backend Platform Engineer",
            "seniority": "Senior / Lead",
            "required_skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "Kubernetes", "AWS"],
            "preferred_skills": ["Microservices", "CI/CD", "Redis", "Distributed Systems"],
            "responsibilities": [
                "Architect high-throughput REST APIs and distributed microservices with Python and FastAPI.",
                "Design and maintain automated CI/CD pipelines across AWS cloud environments.",
                "Optimize PostgreSQL query throughput and implement robust caching strategies.",
                "Mentor engineers, conduct code reviews, and drive architectural best practices."
            ],
            "education_requirement": "B.Sc. in Computer Science or equivalent practical experience",
            "soft_signals": ["Technical Leadership", "Problem Solving", "Cross-Functional Collaboration"],
            "terminology": ["Microservices", "Sub-50ms Latency", "High Availability", "CI/CD"]
        },
        "evidence_map": [
            {
                "requirement": "Python & FastAPI Backend Architecture",
                "status": "Strong Evidence",
                "evidence_text": "Tech Solutions Ltd: \"Architected high-throughput REST APIs using Python and FastAPI, serving 200k daily active requests with sub-50ms p99 latency.\"",
                "confidence": 0.98,
                "recommendation": "Maintain prominent placement in top work experience bullet."
            },
            {
                "requirement": "Docker & Kubernetes Containerization",
                "status": "Strong Evidence",
                "evidence_text": "Tech Solutions Ltd: \"Designed and deployed containerized microservices with Docker and Kubernetes, reducing infrastructure overhead by 40%.\"",
                "confidence": 0.95,
                "recommendation": "Great proof; highlight container cluster management during interviews."
            },
            {
                "requirement": "Automated CI/CD & AWS Cloud",
                "status": "Strong Evidence",
                "evidence_text": "Tech Solutions Ltd: \"Engineered automated CI/CD pipelines integrating GitHub Actions, Docker, and AWS ECR, cutting release cycles from 2 weeks to 3 days.\"",
                "confidence": 0.94,
                "recommendation": "Explicitly reference AWS services (ECR, ECS, CloudWatch) in cover letter."
            },
            {
                "requirement": "PostgreSQL Database Optimization",
                "status": "Strong Evidence",
                "evidence_text": "Tech Solutions Ltd: \"Optimized PostgreSQL query performance through indexing strategies and connection pooling, improving read throughput by 3x.\"",
                "confidence": 0.92,
                "recommendation": "Clear performance outcome; strong evidence."
            },
            {
                "requirement": "Distributed Systems & Caching (Redis)",
                "status": "Partial Evidence",
                "evidence_text": "Listed in Master CV skills: Redis, Distributed Systems.",
                "confidence": 0.75,
                "recommendation": "Add a concrete bullet detailing Redis caching strategies in production."
            },
            {
                "requirement": "Engineering Leadership & Mentorship",
                "status": "Indirect Evidence",
                "evidence_text": "Transferable leadership demonstrated across architecture and cross-team delivery.",
                "confidence": 0.65,
                "recommendation": "State ownership of code reviews and technical direction in executive summary."
            }
        ],
        "match_score_breakdown": {
            "overall_score": 92,
            "match_tier": "High Alignment",
            "interpretation": "92/100, exceptional alignment across core technical and architectural requirements.",
            "requirement_coverage_score": 94,
            "evidence_strength_score": 91,
            "keyword_alignment_score": 95,
            "experience_alignment_score": 88,
            "structure_readability_score": 96,
            "application_coherence_score": 95,
            "actionable_recommendations": [
                "Elevate Redis caching details to strengthen the distributed systems evidence.",
                "Highlight AWS deployment scope in your interview elevator pitch."
            ]
        },
        "factual_integrity": {
            "integrity_score": 100,
            "claims_checked": 28,
            "supported_claims": 28,
            "unsupported_metrics_count": 0,
            "unsupported_warnings": [],
            "status_label": "100% Source-Grounded"
        },
        "recruiter_review": {
            "first_impression_score": 8.8,
            "what_stands_out": [
                "Exceptional quantifiable metrics: 200k daily requests, sub-50ms p99 latency, 3x throughput improvement.",
                "Direct keyword overlap with modern backend stack (FastAPI, Docker, Kubernetes, AWS, PostgreSQL).",
                "Clean, uncluttered technical chronology and top First Class Honors degree."
            ],
            "what_gets_overlooked": [
                "Infrastructure CI/CD automation is positioned in bullet 3; consider mentioning AWS in the executive summary.",
                "Secondary database proficiencies (Redis) can be emphasized in architectural discussions."
            ],
            "potential_concerns": [
                "Ensure willingness to lead cross-functional architecture reviews is stated clearly in cover letter."
            ],
            "recommended_actions": [
                "Generate the tailored cover letter to tie past API scale directly to the target employer's platform goals.",
                "Review the interview prep talking points before screening calls."
            ]
        },
        "interview_prep": {
            "key_talking_points": [
                "How I architected high-throughput FastAPI microservices serving 200k daily requests with sub-50ms p99 latency.",
                "Accelerating deployment velocity by 60% using containerized GitHub Actions and AWS ECR pipelines.",
                "Engineering database connection pooling and indexing strategies that tripled PostgreSQL read throughput."
            ],
            "likely_technical_questions": [
                "How do you approach concurrency, connection pooling, and async workers in FastAPI under peak traffic?",
                "Can you walk through your zero-downtime container deployment strategy using Docker and Kubernetes?",
                "How do you design database schemas and caching layers with PostgreSQL and Redis to handle rapid data growth?"
            ],
            "behavioral_star_prompts": [
                "STAR: Describe a high-stakes production incident or performance bottleneck you identified and resolved under pressure.",
                "STAR: Walk through a situation where you introduced a new DevOps tool or pipeline that saved engineering hours.",
                "STAR: How do you balance code quality, test coverage, and tight product delivery deadlines?"
            ]
        },
        "cover_letter": {
            "recipient_title": "Dear Hiring Team,",
            "recipient_name": "Selection Committee & Technology Practice Leads",
            "company_name": "Horizon Enterprise Consulting",
            "department_or_address": "Enterprise Cloud & Transformation Practice",
            "job_title": "Senior Digital Transformation & Cloud Strategy Lead",
            "paragraphs": [
                "I am writing to express my enthusiastic interest in the Senior Digital Transformation & Cloud Strategy Lead position with Horizon Enterprise Consulting. Having spearheaded multi-million euro modernization initiatives across DACH financial services and public sector clients, I am eager to bring my 8+ years track record in enterprise cloud architecture, agile delivery, and process automation to your consulting practice. My career has focused on translating intricate business mandates into resilient, scalable technology solutions that deliver measurable ROI.",
                "Throughout my recent tenure at Alpine Digital Consulting and Vienna Technology Group, I have specialized in cloud modernization and business process optimization. Notably, I orchestrated an Azure cloud modernization roadmap for 200+ users that reduced enterprise hosting costs by 25% while maintaining zero unscheduled downtime. Furthermore, I engineered an automated financial reconciliation pipeline using Python, SQL, and Power BI that eliminated 35% of manual reporting overhead and condensed monthly close cycles from five days to under eight hours.",
                "Beyond technical depth, I bring proven executive stakeholder management and cross-functional leadership experience. Certified in Agile project management (PSM I) and ITIL 4, I regularly facilitate discovery workshops with C-suite stakeholders, align disparate departmental priorities, and lead blended teams of engineers and business analysts. I am passionate about establishing sustainable cloud governance and AI adoption frameworks that enable teams to innovate safely and effectively.",
                "Horizon Enterprise Consulting's reputation for driving transformative, client-centric enterprise solutions strongly aligns with my professional values and career trajectory. I would welcome the opportunity to discuss in detail how my cloud transformation expertise, analytical rigor, and client leadership will contribute to the ongoing success of your practice. Thank you for your time and consideration; I look forward to speaking with your hiring team."
            ],
            "sign_off": "Sincerely,"
        }
    })


@app.route("/api/optimize", methods=["POST"])
@app.route("/api/optimize/", methods=["POST"])
@app.route("/cv_studio/api/optimize", methods=["POST"])
@app.route("/cv_studio/api/optimize/", methods=["POST"])
@app.route("/cv_optimizer/api/optimize", methods=["POST"])
@app.route("/cv_optimizer/api/optimize/", methods=["POST"])
def optimize_cv_endpoint():
    """Optimizes a candidate resume against a job description."""
    session_id = str(uuid.uuid4())[:8]

    api_key = request.form.get("api_key")
    if api_key and api_key.strip():
        os.environ["OPENAI_API_KEY"] = api_key.strip()

    resume_file = request.files.get("resume_file")
    resume_text = request.form.get("resume_text")
    jd_file = request.files.get("jd_file")
    jd_text = request.form.get("jd_text")
    use_mock = request.form.get("use_mock", "false").lower() in ["true", "1", "yes"]
    parse_model = request.form.get("parse_model", DEFAULT_MODEL)
    optimize_model = request.form.get("optimize_model", DEFAULT_MODEL)
    template_style = request.form.get("template_style", "modern_two_column")
    columns = int(request.form.get("columns", 1))
    font_name = request.form.get("font_name", "Outfit")

    # Determine CV source
    temp_cv_path = None
    if resume_file and resume_file.filename:
        ext = Path(resume_file.filename).suffix.lower()
        temp_cv_path = UPLOADS_DIR / f"cv_{session_id}{ext}"
        resume_file.save(str(temp_cv_path))
    elif resume_text and resume_text.strip():
        temp_cv_path = UPLOADS_DIR / f"cv_{session_id}.txt"
        temp_cv_path.write_text(resume_text.strip(), encoding="utf-8")
    else:
        return jsonify({"detail": "Please upload a resume file or paste resume text."}), 400

    # Determine JD source
    temp_jd_path = None
    if jd_file and jd_file.filename:
        ext = Path(jd_file.filename).suffix.lower()
        temp_jd_path = UPLOADS_DIR / f"jd_{session_id}{ext}"
        jd_file.save(str(temp_jd_path))
    elif jd_text and jd_text.strip():
        temp_jd_path = UPLOADS_DIR / f"jd_{session_id}.txt"
        temp_jd_path.write_text(jd_text.strip(), encoding="utf-8")
    else:
        return jsonify({"detail": "Please upload a job description file or paste job requirements."}), 400

    output_filename = f"Tailored_ATS_Resume_{session_id}.docx"
    output_docx_path = OUTPUTS_DIR / output_filename

    try:
        result = run_cv_optimization_pipeline(
            input_cv_path=str(temp_cv_path),
            input_jd_path=str(temp_jd_path),
            output_docx_path=str(output_docx_path),
            use_mock=use_mock,
            parse_model=parse_model,
            optimize_model=optimize_model,
            template_style=template_style,
            columns=columns,
            font_name=font_name
        )

        cand_name = ""
        if result.get("tailored_cv") and hasattr(result["tailored_cv"], "contact") and result["tailored_cv"].contact:
            cand_name = getattr(result["tailored_cv"].contact, "full_name", "")
        if not cand_name and result.get("parsed_resume") and hasattr(result["parsed_resume"], "contact") and result["parsed_resume"].contact:
            cand_name = getattr(result["parsed_resume"].contact, "full_name", "")

        role_t = ""
        comp_n = ""
        if result.get("parsed_jd"):
            role_t = getattr(result["parsed_jd"], "job_title", "")
            comp_n = getattr(result["parsed_jd"], "company_name", "")
        if not role_t and result.get("job_model"):
            role_t = getattr(result["job_model"], "role_title", "")

        # Concurrently build tailored Cover Letter so it is available immediately
        cover_letter_data = build_tailored_cover_letter_data(
            tailored_cv=result["tailored_cv"].model_dump() if hasattr(result.get("tailored_cv"), "model_dump") else (result.get("tailored_cv") or {}),
            job_reqs=result["job_model"].model_dump() if hasattr(result.get("job_model"), "model_dump") else (result.get("parsed_jd").model_dump() if hasattr(result.get("parsed_jd"), "model_dump") else (result.get("parsed_jd") or {}))
        )

        return jsonify({
            "success": True,
            "session_id": session_id,
            "download_url": f"/api/download/{output_filename}",
            "filename": output_filename,
            "template_style": template_style,
            "columns": columns,
            "font_name": font_name,
            "candidate_name": cand_name,
            "role_title": role_t,
            "company_name": comp_n,
            "cover_letter": cover_letter_data,
            "job_requirements": result["parsed_jd"].model_dump() if hasattr(result.get("parsed_jd"), "model_dump") else result.get("parsed_jd"),
            "audit_report": result["audit_report"],
            "keyword_coverage": result["keyword_coverage"],
            "parsed_resume": result["parsed_resume"].model_dump(),
            "parsed_jd": result["parsed_jd"].model_dump(),
            "tailored_cv": result["tailored_cv"].model_dump(),
            "job_model": result["job_model"].model_dump(),
            "evidence_map": [item.model_dump() for item in result["evidence_map"]],
            "match_score_breakdown": result["match_score_breakdown"].model_dump(),
            "factual_integrity": result["factual_integrity"].model_dump(),
            "recruiter_review": result["recruiter_review"].model_dump(),
            "interview_prep": result["interview_prep"].model_dump()
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"detail": f"Pipeline optimization failed: {str(e)}"}), 500

    finally:
        if temp_cv_path and temp_cv_path.exists():
            try:
                temp_cv_path.unlink()
            except Exception:
                pass
        if temp_jd_path and temp_jd_path.exists():
            try:
                temp_jd_path.unlink()
            except Exception:
                pass


@app.route("/api/export-custom-docx", methods=["POST"])
@app.route("/cv_studio/api/export-custom-docx", methods=["POST"])
@app.route("/cv_optimizer/api/export-custom-docx", methods=["POST"])
def export_custom_docx_endpoint():
    """Renders a tailored Word document from live-edited browser state."""
    payload = request.get_json(force=True, silent=True) or {}
    doc_title = payload.get("doc_title") or payload.get("filename")
    if doc_title:
        clean_title = re.sub(r'[^a-zA-Z0-9_\- ]', '', str(doc_title)).strip().replace(' ', '_')
        if not clean_title.endswith('.docx'):
            clean_title += '.docx'
        output_filename = clean_title
    else:
        session_id = str(uuid.uuid4())[:8]
        output_filename = f"Tailored_ATS_Resume_{session_id}.docx"

    output_docx_path = OUTPUTS_DIR / output_filename

    try:
        tailored_data = payload.get("tailored_cv", {})
        contact_data = payload.get("contact_info", {})
        template_style = payload.get("template_style", "modern_two_column")
        columns = int(payload.get("columns", 1))
        font_name = payload.get("font_name", "Outfit")

        if "work_experience" in tailored_data and isinstance(tailored_data["work_experience"], list):
            norm_exp_list = []
            for exp in tailored_data["work_experience"]:
                if isinstance(exp, dict):
                    exp_dict = dict(exp)
                    if "company" not in exp_dict and "company_name" in exp_dict:
                        exp_dict["company"] = exp_dict["company_name"]
                    elif "company" not in exp_dict:
                        exp_dict["company"] = "Company"
                    
                    bullets = exp_dict.get("bullet_points", [])
                    norm_bullets = []
                    for b in bullets:
                        if isinstance(b, str):
                            norm_bullets.append({"optimized_text": b, "original_text": b, "reasoning_steps": ""})
                        elif isinstance(b, dict):
                            if "optimized_text" not in b:
                                text_val = b.get("text", "") or b.get("description", "") or "Accomplishment"
                                b_dict = dict(b)
                                b_dict["optimized_text"] = text_val
                                norm_bullets.append(b_dict)
                            else:
                                norm_bullets.append(b)
                    exp_dict["bullet_points"] = norm_bullets
                    norm_exp_list.append(exp_dict)
                else:
                    norm_exp_list.append(exp)
            tailored_data["work_experience"] = norm_exp_list

        contact_info = ContactInformation(**contact_data) if contact_data else ContactInformation(full_name="Candidate", email="candidate@example.com")
        if "contact" not in tailored_data or not tailored_data["contact"]:
            tailored_data["contact"] = contact_info.model_dump()
        if "professional_summary" not in tailored_data or not tailored_data["professional_summary"]:
            tailored_data["professional_summary"] = "Experienced professional with background in software systems and engineering."
        if "work_experience" not in tailored_data:
            tailored_data["work_experience"] = []
        if "education" not in tailored_data:
            tailored_data["education"] = []
        if "skills_section" not in tailored_data:
            tailored_data["skills_section"] = []
        if "skill_categories" not in tailored_data:
            tailored_data["skill_categories"] = []

        tailored_cv = TailoredResumeSchema(**tailored_data)
        list_style = payload.get("list_style", "disc")

        saved_path = build_ats_friendly_docx(
            data=tailored_cv,
            contact_info=contact_info,
            output_path=output_docx_path,
            template_style=template_style,
            columns=columns,
            font_name=font_name,
            list_style=list_style
        )

        return jsonify({
            "success": True,
            "download_url": f"/api/download/{output_filename}",
            "filename": output_filename
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"detail": f"Failed to generate Word document: {str(e)}"}), 500


@app.route("/api/generate-cover-letter", methods=["POST"])
@app.route("/api/generate-cover-letter/", methods=["POST"])
@app.route("/cv_studio/api/generate-cover-letter", methods=["POST"])
@app.route("/cv_studio/api/generate-cover-letter/", methods=["POST"])
@app.route("/cv_optimizer/api/generate-cover-letter", methods=["POST"])
@app.route("/cv_optimizer/api/generate-cover-letter/", methods=["POST"])
def generate_cover_letter_endpoint():
    """Generates a tailored Cover Letter."""
    payload = request.get_json(force=True, silent=True) or {}
    resume_context = payload.get("resume_context", "")
    jd_context = payload.get("jd_context", "")
    tailored_cv = payload.get("tailored_cv_context", {})
    job_reqs = payload.get("job_requirements_context", {})

    cover_letter_data = build_tailored_cover_letter_data(
        tailored_cv=tailored_cv,
        job_reqs=job_reqs,
        resume_context=resume_context,
        jd_context=jd_context
    )
    return jsonify({
        "success": True,
        "cover_letter": cover_letter_data
    })


@app.route("/api/export-cover-letter-docx", methods=["POST"])
@app.route("/cv_studio/api/export-cover-letter-docx", methods=["POST"])
@app.route("/cv_optimizer/api/export-cover-letter-docx", methods=["POST"])
def export_cover_letter_docx_endpoint():
    """Renders an ATS-compliant Word document for the generated Cover Letter."""
    payload = request.get_json(force=True, silent=True) or {}
    contact_data = payload.get("contact_info", {})
    paragraphs = payload.get("paragraphs", [])
    salutation = payload.get("salutation", "Dear Hiring Team,")
    sign_off = payload.get("sign_off", "Sincerely,")
    font_name = payload.get("font_name", "Outfit")
    doc_title = payload.get("doc_title", "Tailored_Cover_Letter")

    clean_title = re.sub(r'[^a-zA-Z0-9_\- ]', '', str(doc_title)).strip().replace(' ', '_')
    if not clean_title.endswith('.docx'):
        clean_title += '.docx'

    output_docx_path = OUTPUTS_DIR / clean_title
    template_style = payload.get("template_style", "cl_template_1_centered")

    try:
        contact_info = ContactInformation(**contact_data)
        saved_path = build_cover_letter_docx(
            contact_info=contact_info,
            paragraphs=paragraphs,
            salutation=salutation,
            sign_off=sign_off,
            output_path=output_docx_path,
            font_name=font_name,
            template_style=template_style
        )

        return jsonify({
            "success": True,
            "download_url": f"/api/download/{clean_title}",
            "filename": clean_title
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"detail": f"Failed to generate Cover Letter Word document: {str(e)}"}), 500


@app.route("/api/chat", methods=["POST"])
@app.route("/api/chat/", methods=["POST"])
@app.route("/cv_studio/api/chat", methods=["POST"])
@app.route("/cv_studio/api/chat/", methods=["POST"])
@app.route("/cv_optimizer/api/chat", methods=["POST"])
@app.route("/cv_optimizer/api/chat/", methods=["POST"])
def ai_assistant_chat():
    """Conversational AI Assistant discussion endpoint."""
    payload = request.get_json(force=True, silent=True) or {}
    messages = payload.get("messages", [])
    candidate_name = payload.get("candidate_name", "").strip()
    current_role = payload.get("current_role", "").strip()
    resume_context = payload.get("resume_context", "")
    jd_context = payload.get("jd_context", "")
    tailored_cv_context = payload.get("tailored_cv_context", None)
    cover_letter_context = payload.get("cover_letter_context", "")
    active_mode = payload.get("active_mode", "cv")

    client = None
    try:
        client = get_openai_client()
    except Exception:
        client = None

    if client and os.environ.get("OPENAI_API_KEY"):
        system_content = f"""You are an elite Senior Technical Recruiter, Hiring Manager, and ATS Optimization Strategist.
You are assisting the user in real-time as they review and optimize their professional documents in CV Studio.

=== ACTIVE CANDIDATE PROFILE ===
CANDIDATE NAME: {candidate_name or 'Candidate currently shown in the active document'}
PROFESSIONAL TITLE / ROLE: {current_role or 'As specified in the active document'}
CURRENT VIEW MODE: {active_mode.upper()} ({'Reviewing Curriculum Vitae' if active_mode == 'cv' else 'Reviewing Cover Letter'})

=== ACTIVE CV CONTENT (CURRENTLY ON SCREEN) ===
{resume_context or 'No CV content available.'}

=== ACTIVE COVER LETTER CONTENT (CURRENTLY ON SCREEN) ===
{cover_letter_context or 'No Cover Letter generated yet.'}

=== TARGET JOB DESCRIPTION / REQUIREMENTS ===
{jd_context or 'No target job description specified.'}

=== CRITICAL BEHAVIORAL DIRECTIVES ===
1. IDENTITY STRICTNESS: You are analyzing the CV / Cover Letter for {candidate_name or 'the candidate above'}. Always refer to {candidate_name or 'the candidate'} and their exact qualifications provided above.
2. ACCURACY & CONTEXT: Base all analysis, strengths, gaps, ATS keyword recommendations, and rewrites strictly on the candidate's actual work experience, education, skills, and target job description shown above.
3. CONSTRUCTIVE COACHING: Provide structured, actionable, and encouraging feedback with practical bullet points.
4. Keep your tone professional, highly insightful, encouraging, and career-advancement focused."""

        api_messages = [{"role": "system", "content": system_content}]
        for msg in messages:
            if msg.get("role") in ["user", "assistant"]:
                content_str = str(msg.get("content", "")).strip()
                if content_str:
                    api_messages.append({
                        "role": msg["role"],
                        "content": content_str
                    })

        def _call():
            response = client.chat.completions.create(
                model=DEFAULT_MODEL,
                messages=api_messages,
                max_completion_tokens=4096
            )
            return response.choices[0].message.content

        try:
            reply = safe_execute_with_retry(_call)
            return jsonify({"success": True, "reply": reply})
        except Exception as e:
            print(f"OpenAI chat call fallback triggered: {e}")

    # Fallback to intelligent offline assistant response
    last_msg = messages[-1].get("content", "") if messages else ""
    reply = generate_heuristic_assistant_reply(
        user_message=last_msg,
        candidate_name=candidate_name,
        current_role=current_role,
        resume_context=resume_context,
        jd_context=jd_context,
        active_mode=active_mode
    )
    return jsonify({"success": True, "reply": reply, "mode": "heuristic"})


@app.route("/api/rewrite-snippet", methods=["POST"])
@app.route("/cv_studio/api/rewrite-snippet", methods=["POST"])
@app.route("/cv_optimizer/api/rewrite-snippet", methods=["POST"])
def rewrite_snippet_endpoint():
    """Rewrites a specific selected sentence, bullet point, or paragraph."""
    payload = request.get_json(force=True, silent=True) or {}
    text_to_rewrite = payload.get("text", "").strip()
    instruction = payload.get("instruction", "Make it more impactful, executive, and compelling").strip()
    jd_context = payload.get("jd_context", "")
    resume_context = payload.get("resume_context", "")

    if not text_to_rewrite:
        return jsonify({"detail": "No text provided to rewrite."}), 400

    client = get_openai_client()

    system_prompt = """You are an expert Technical Writer and Executive Career Strategist.
Your mission is to rewrite the provided text snippet (sentence, bullet point, or paragraph) according to the user's instruction.

RULES:
1. Return ONLY the rewritten text snippet. Do not include introductory remarks, quotes, or conversational preamble.
2. Keep the meaning factually true to the candidate's background without fabricating unverified metrics.
3. Enhance impact, action verbs, clarity, and keyword resonance."""

    user_prompt = f"""ORIGINAL TEXT TO REWRITE:
\"\"\"{text_to_rewrite}\"\"\"

INSTRUCTION / GOAL:
{instruction}

TARGET JOB CONTEXT:
{jd_context or 'Software Engineering'}

CANDIDATE PROFILE CONTEXT:
{resume_context or 'Computer Science / Engineering'}

Provide the improved rewrite:"""

    def _call():
        response = client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_completion_tokens=2048
        )
        return response.choices[0].message.content.strip()

    try:
        rewritten = safe_execute_with_retry(_call)
        if rewritten.startswith('"') and rewritten.endswith('"'):
            rewritten = rewritten[1:-1].strip()
        return jsonify({
            "success": True,
            "original_text": text_to_rewrite,
            "rewritten_text": rewritten
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"detail": f"Snippet rewrite failed: {str(e)}"}), 500


@app.route("/api/download/<filename>", methods=["GET"])
@app.route("/cv_studio/api/download/<filename>", methods=["GET"])
@app.route("/cv_optimizer/api/download/<filename>", methods=["GET"])
def download_document(filename: str):
    """Serves the generated ATS DOCX file for download."""
    safe_filename = Path(filename).name
    file_path = OUTPUTS_DIR / safe_filename

    if not file_path.exists():
        abort(404, description="Requested resume document not found.")

    return send_from_directory(
        directory=str(OUTPUTS_DIR),
        path=safe_filename,
        as_attachment=True,
        download_name=safe_filename,
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )


@app.route("/api/recommend-sections", methods=["POST"])
@app.route("/cv_studio/api/recommend-sections", methods=["POST"])
@app.route("/cv_optimizer/api/recommend-sections", methods=["POST"])
def recommend_sections_endpoint():
    payload = request.get_json(force=True, silent=True) or {}
    if payload.get("resume_text"):
        resume_data = heuristic_parse_resume(payload["resume_text"])
    else:
        resume_data = payload.get("resume_data") or payload.get("tailored_cv") or payload.get("parsed_resume") or payload
    job_desc = payload.get("job_description") or payload.get("jd_text") or ""
    result = recommend_sections_for_candidate(resume_data, job_desc)
    return jsonify(result.model_dump())


@app.route("/api/validate-cv", methods=["POST"])
@app.route("/cv_studio/api/validate-cv", methods=["POST"])
@app.route("/cv_optimizer/api/validate-cv", methods=["POST"])
def validate_cv_endpoint():
    payload = request.get_json(force=True, silent=True) or {}
    source_resume = payload.get("source_resume") or payload.get("parsed_resume")
    if not source_resume and payload.get("resume_text"):
        source_resume = heuristic_parse_resume(payload["resume_text"])
    rendered_cv = payload.get("rendered_cv") or payload.get("tailored_cv")
    if not rendered_cv:
        rendered_cv = source_resume or payload
    current_template = payload.get("template_name") or payload.get("current_template") or ""
    report = audit_information_loss(source_resume or payload, rendered_cv, current_template=current_template)
    return jsonify(report.model_dump())


@app.route("/api/quality-score", methods=["POST"])
@app.route("/cv_studio/api/quality-score", methods=["POST"])
@app.route("/cv_optimizer/api/quality-score", methods=["POST"])
def quality_score_endpoint():
    payload = request.get_json(force=True, silent=True) or {}
    if payload.get("resume_text"):
        cv_data = heuristic_parse_resume(payload["resume_text"])
    else:
        cv_data = payload.get("tailored_cv") or payload.get("cv_data") or payload
    target_job = payload.get("job_model") or payload.get("job_description")
    score_breakdown = calculate_cv_quality_score(cv_data, target_job)
    return jsonify(score_breakdown.model_dump())


@app.route("/api/stress-test-data", methods=["GET"])
@app.route("/cv_studio/api/stress-test-data", methods=["GET"])
@app.route("/cv_optimizer/api/stress-test-data", methods=["GET"])
def get_stress_test_data_endpoint():
    payload = get_29_section_stress_cv_payload()
    raw_resume = payload["raw_markdown_resume"]
    raw_jd = payload["job_description"]

    parsed = heuristic_parse_resume(raw_resume)
    job_reqs = parse_job_description(raw_jd)
    tailored = mock_optimize_pipeline(parsed, job_reqs)
    quality = calculate_cv_quality_score(parsed)
    loss_report = audit_information_loss(parsed, tailored, current_template="template_ats_minimal")
    recs = recommend_sections_for_candidate(parsed)
    job_model = extract_structured_job_model(raw_jd)
    evidence_items = heuristic_generate_evidence_map(parsed, job_model)

    response_data = {
        "success": True,
        "candidate_name": parsed.contact.full_name if (parsed and parsed.contact and parsed.contact.full_name) else "Dr. Elena Vance",
        "role_title": job_reqs.job_title if (job_reqs and job_reqs.job_title) else "IT Support Specialist",
        "company_name": job_reqs.company_name if (job_reqs and job_reqs.company_name) else "OmniTech Solutions",
        "parsed_jd": job_reqs.model_dump() if hasattr(job_reqs, 'model_dump') else job_reqs,
        "job_requirements": job_reqs.model_dump() if hasattr(job_reqs, 'model_dump') else job_reqs,
        "job_model": job_model.model_dump() if hasattr(job_model, 'model_dump') else job_model,
        "resume_text": raw_resume,
        "job_description_text": raw_jd,
        "raw_markdown_resume": raw_resume,
        "contact_info": payload["contact_info"],
        "expected_section_count": 29,
        "parsed_resume": parsed.model_dump(),
        "tailored_cv": tailored.model_dump(),
        "quality_score": quality.model_dump(),
        "loss_audit": loss_report.model_dump(),
        "section_recommendations": recs.model_dump(),
        "evidence_map": [e.model_dump() if hasattr(e, 'model_dump') else e for e in evidence_items]
    }
    return jsonify(response_data)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=True)
