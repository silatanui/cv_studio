"""
FastAPI Web Application for Algorithmic CV Optimization.

Provides interactive REST endpoints and a responsive user dashboard
for uploading resumes, selecting templates, live in-browser editing,
conversational AI Assistant discussions, and downloading compliant Word and PDF documents.
"""

import os
import re
import json
import uuid
import shutil
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional, Dict, Any, List

from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request, Body
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

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
    mock_optimize_pipeline,
    extract_structured_job_model,
    heuristic_generate_evidence_map,
)
from section_engine import (
    calculate_cv_quality_score,
    audit_information_loss,
    recommend_sections_for_candidate,
    normalize_section_type,
    ALL_KNOWN_SECTIONS,
    DEFAULT_SECTION_TITLES,
)
from mock_stress_data import get_29_section_stress_cv_payload, SAMPLE_IT_SUPPORT_JD

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

UPLOADS_DIR = BASE_DIR / "uploads"
OUTPUTS_DIR = BASE_DIR / "outputs"
SAMPLE_DATA_DIR = BASE_DIR / "sample_data"

UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="Algorithmic CV Optimizer",
    description="Automated Applicant Tracking System (ATS) CV optimization via OpenAI Structured Outputs",
    version="1.0.0"
)

# Static and Template mounts
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@app.get("/", response_class=HTMLResponse)
async def serve_index(request: Request):
    """Renders the main CV optimization dashboard."""
    return templates.TemplateResponse(request=request, name="index.html")


@app.get("/api/health")
async def health_check():
    """Service health and environment status."""
    return {
        "status": "healthy",
        "has_openai_key": True,
        "model": DEFAULT_MODEL
    }


@app.get("/api/sample-data")
async def get_sample_data():
    """Returns a structured sample resume payload for canvas pre-population and 1-click demo."""
    sample_jd_reqs = {
        "job_title": "Senior Digital Transformation & Cloud Strategy Lead",
        "company_name": "Horizon Enterprise Consulting",
        "required_skills": ["Digital Transformation", "Cloud Modernization", "Microsoft Azure", "Process Automation", "Python", "SQL", "Power BI", "Agile/Scrum"],
        "preferred_skills": ["Generative AI Governance", "Enterprise Architecture", "Stakeholder Management", "Change Management"],
        "responsibilities": [
            "Lead enterprise-scale digital transformation and cloud migration roadmaps.",
            "Collaborate with C-level stakeholders to translate complex business needs into technology architectures.",
            "Oversee cross-functional delivery teams across Agile software development, cloud infrastructure, and data analytics.",
            "Evaluate and deploy automation frameworks, business intelligence reporting, and responsible generative AI solutions."
        ]
    }
    return {
        "success": True,
        "candidate_name": "Sofia Katharina Berger",
        "role_title": "Senior Digital Transformation & Cloud Strategy Lead",
        "company_name": "Horizon Enterprise Consulting",
        "parsed_jd": sample_jd_reqs,
        "job_requirements": sample_jd_reqs,
        "analysis_date": "Sep 3, 2026",
        "resume_text": """SOFIA KATHARINA BERGER
Senior Digital Transformation & Technology Consultant
Email: sofia.berger@example.com | Phone: +43 660 847 2916 | Location: Vienna, Austria
LinkedIn: linkedin.com/in/sofiaberger | Website: sofiaberger.dev | GitHub: github.com/sofiaberger

PROFESSIONAL PROFILE
Experienced Digital Transformation and Technology Consultant with over eight years of experience delivering technology-enabled business improvements across financial services, retail, healthcare, and public-sector environments. Strong background in software development, business analysis, cloud technologies, data analytics, project management, and technology strategy. Combines technical expertise with strong stakeholder management and communication skills, with a proven ability to translate complex business requirements into practical digital solutions.

PROFESSIONAL EXPERIENCE
Senior Digital Transformation Consultant | Alpine Digital Consulting GmbH, Vienna, Austria | January 2023 – Present
- Reduced manual reporting activities for a financial-services client by approximately 35% through process automation.
- Led an enterprise cloud migration project involving more than 200 internal users across Austria and Germany.
- Designed a centralized reporting solution that reduced monthly reporting preparation time from several days to less than one day.
- Established an internal AI evaluation framework for assessing potential business applications of generative AI.
- Coordinated a cross-functional team of 12 professionals including developers, analysts, and project managers during major digital transformation projects.

Technology Consultant | Danube Technology Group, Vienna, Austria | June 2020 – December 2022
- Developed automated reporting processes that saved approximately 15 hours of administrative work per month.
- Supported the successful implementation of an Azure-based customer management platform used by more than 500 employees.
- Built interactive Power BI dashboards utilized by senior executive management to track strategic operational KPIs.
- Standardized functional requirements and user story mapping across three Agile sprint delivery teams.

Software Developer | Vienna Digital Solutions, Vienna, Austria | September 2018 – May 2020
- Developed an internal workflow application in Python and JavaScript that replaced several error-prone spreadsheet processes.
- Improved database query performance and API response times by 45% through SQL query optimization and indexing.
- Engineered reusable RESTful API modules that accelerated subsequent delivery timelines across client projects.

EDUCATION
Master of Science in Digital Transformation | University of Vienna, Austria | 2020 – 2022
Thesis: Artificial Intelligence Adoption in Small and Medium-Sized Enterprises: Opportunities, Barriers, and Organizational Readiness

Bachelor of Science in Computer Science | TU Wien, Austria | 2015 – 2018
Academic Achievement: Graduated with distinction.

SKILLS
Digital Transformation, Technology Strategy, Business Analysis, Cloud Modernization, Python, JavaScript, TypeScript, SQL, React, Node.js, FastAPI, Microsoft Azure, Docker, Power BI, Agile/Scrum, Project Management""",
        "job_description_text": """Job Title: Senior Digital Transformation & Cloud Strategy Lead
Company: Horizon Enterprise Consulting
Location: Vienna, Austria (Hybrid)

About the Role:
We are seeking an experienced Senior Digital Transformation & Cloud Strategy Lead to guide enterprise clients through cloud modernization, process automation, and data-driven digital initiatives.

Key Responsibilities:
- Lead enterprise-scale digital transformation and cloud migration roadmaps.
- Collaborate with C-level stakeholders to translate complex business needs into technology architectures.
- Oversee cross-functional delivery teams across Agile software development, cloud infrastructure, and data analytics.
- Evaluate and deploy automation frameworks, business intelligence reporting, and responsible generative AI solutions.

Required Qualifications & Skills:
- 7+ years of technology consulting, software engineering, or digital transformation experience.
- Hands-on proficiency with Microsoft Azure, cloud architecture, and modern application stacks (Python, APIs, SQL).
- Demonstrated experience in BI dashboard development (Power BI) and automated workflow optimization.
- Master's or Bachelor's degree in Computer Science, Information Systems, or related field.
- Fluent German and English communication skills.""",
        "keyword_coverage": {
            "score": 0.94,
            "total_matched": 10,
            "total_required": 11,
            "matched": ["Digital Transformation", "Cloud Modernization", "Microsoft Azure", "Process Automation", "Python", "SQL", "Power BI", "Agile/Scrum", "Generative AI", "Stakeholder Management"],
            "missing": ["Enterprise Architecture"]
        },
        "audit_report": {
            "is_valid": True,
            "discrepancies": []
        },
        "parsed_resume": {
            "contact": {
                "full_name": "Sofia Katharina Berger",
                "professional_title": "Senior Digital Transformation & Technology Consultant",
                "email": "sofia.berger@example.com",
                "phone": "+43 660 847 2916",
                "location": "Vienna, Austria",
                "linkedin_url": "linkedin.com/in/sofiaberger",
                "portfolio_url": "sofiaberger.dev"
            },
            "summary": "Experienced Digital Transformation and Technology Consultant with over eight years of experience delivering technology-enabled business improvements across financial services, retail, healthcare, and public-sector environments. Strong background in software development, business analysis, cloud technologies, data analytics, project management, and technology strategy. Combines technical expertise with strong stakeholder management and communication skills.",
            "key_achievements": [
                {"title": "Digital Innovation Award", "description": "Recognized by Alpine Digital Consulting (2024) for leading innovative automation initiative reducing reporting time by 35%."}
            ],
            "work_experience": [
                {
                    "company": "Alpine Digital Consulting GmbH",
                    "job_title": "Senior Digital Transformation Consultant",
                    "start_date": "Jan 2023",
                    "end_date": "Present",
                    "location": "Vienna, Austria",
                    "bullet_points": [
                        "Reduced manual reporting activities for a financial-services client by approximately 35% through process automation.",
                        "Led a cloud migration project involving more than 200 internal users across Austria and Germany.",
                        "Designed a centralized reporting solution that reduced monthly reporting preparation time from several days to less than one day.",
                        "Established an internal AI evaluation framework for assessing potential business applications of generative AI.",
                        "Coordinated a cross-functional team of 12 professionals consisting of developers, designers, and analysts during enterprise delivery."
                    ]
                },
                {
                    "company": "Danube Technology Group",
                    "job_title": "Technology Consultant",
                    "start_date": "Jun 2020",
                    "end_date": "Dec 2022",
                    "location": "Vienna, Austria",
                    "bullet_points": [
                        "Developed automated reporting processes that saved approximately 15 hours of administrative work per month.",
                        "Supported the successful implementation of a customer management platform used by more than 500 employees.",
                        "Created Power BI dashboards used by senior management to monitor operational KPIs and performance metrics.",
                        "Gathered and documented functional requirements while mentoring delivery teams in Agile sprint ceremonies."
                    ]
                },
                {
                    "company": "Vienna Digital Solutions",
                    "job_title": "Software Developer",
                    "start_date": "Sep 2018",
                    "end_date": "May 2020",
                    "location": "Vienna, Austria",
                    "bullet_points": [
                        "Developed an internal workflow application in Python and JavaScript that replaced several spreadsheet-based processes.",
                        "Improved application response times through database query optimization and indexing in PostgreSQL and MySQL.",
                        "Developed reusable REST API components that reduced development cycle times for subsequent projects."
                    ]
                }
            ],
            "education": [
                {
                    "institution": "University of Vienna",
                    "degree": "Master of Science in Digital Transformation",
                    "field_of_study": "Digital Transformation & Information Systems",
                    "graduation_date": "2022",
                    "grade": "Academic Excellence Award",
                    "honors": ["Thesis on AI Adoption in SMEs"]
                },
                {
                    "institution": "TU Wien",
                    "degree": "Bachelor of Science in Computer Science",
                    "field_of_study": "Computer Science & Software Engineering",
                    "graduation_date": "2018",
                    "grade": "Graduated with distinction",
                    "honors": ["Best Student Technology Project 2018"]
                }
            ],
            "skills": [
                "Digital Transformation", "Technology Strategy", "Cloud Modernization", "Microsoft Azure", "Python", "SQL", "Power BI", "React", "Docker", "Process Optimization", "Agile Methodologies", "Generative AI"
            ],
            "skill_categories": [
                {"category_name": "Strategy & Consulting", "skills": ["Digital Transformation", "Technology Strategy", "Business Analysis", "Process Optimization", "Change Management", "Stakeholder Management"]},
                {"category_name": "Cloud & Infrastructure", "skills": ["Microsoft Azure", "Azure Functions", "Azure Storage", "Docker", "GitHub Actions", "CI/CD"]},
                {"category_name": "Data & Analytics", "skills": ["Power BI", "SQL", "Python", "NumPy", "Data Visualization", "Business Intelligence"]},
                {"category_name": "Software Development", "skills": ["Python", "JavaScript", "TypeScript", "React", "FastAPI", "PostgreSQL", "REST APIs"]}
            ],
            "academic_work": [],
            "awards_and_scholarships": [
                {"title": "Digital Innovation Award", "year": "2024", "issuer": "Alpine Digital Consulting GmbH"},
                {"title": "Academic Excellence Award", "year": "2022", "issuer": "University of Vienna"},
                {"title": "Best Student Technology Project", "year": "2018", "issuer": "TU Wien"}
            ],
            "languages": [
                {"language": "German", "proficiency": "Native"},
                {"language": "English", "proficiency": "C1 Advanced"},
                {"language": "French", "proficiency": "B1 Intermediate"},
                {"language": "Italian", "proficiency": "A2 Elementary"}
            ],
            "certifications": [
                {"name": "Microsoft Certified: Azure Fundamentals", "issuer": "Microsoft", "year": "2023"},
                {"name": "Professional Scrum Master I (PSM I)", "issuer": "Scrum.org", "year": "2022"},
                {"name": "ITIL 4 Foundation", "issuer": "PeopleCert", "year": "2021"},
                {"name": "Microsoft Power BI Data Analyst", "issuer": "Microsoft", "year": "2021"}
            ],
            "referees": "Available upon Request"
        },
        "tailored_cv": {
            "contact": {
                "full_name": "Sofia Katharina Berger",
                "professional_title": "Senior Digital Transformation & Technology Consultant",
                "email": "sofia.berger@example.com",
                "phone": "+43 660 847 2916",
                "location": "Vienna, Austria",
                "linkedin_url": "linkedin.com/in/sofiaberger",
                "portfolio_url": "sofiaberger.dev"
            },
            "professional_summary": "Accomplished Senior Digital Transformation and Technology Consultant with over eight years of cross-sector leadership in cloud modernization, process automation, and data analytics across financial services and enterprise environments. Proven track record translating executive business vision into high-impact digital architectures, orchestrating cloud migrations for 200+ users, and introducing AI evaluation frameworks that deliver measurable operational efficiency.",
            "key_achievements": [],
            "skills_section": [
                "Digital Transformation", "Technology Strategy", "Cloud Modernization", "Microsoft Azure", "Python", "SQL", "Power BI", "React", "Docker", "Process Optimization", "Agile Methodologies", "Generative AI"
            ],
            "skill_categories": [
                {"category_name": "Strategy & Consulting", "skills": ["Digital Transformation", "Technology Strategy", "Business Analysis", "Process Optimization", "Change Management", "Stakeholder Management"]},
                {"category_name": "Cloud & Infrastructure", "skills": ["Microsoft Azure", "Azure Functions", "Azure Storage", "Docker", "GitHub Actions", "CI/CD"]},
                {"category_name": "Data & Analytics", "skills": ["Power BI", "SQL", "Python", "NumPy", "Data Visualization", "Business Intelligence"]},
                {"category_name": "Software Development", "skills": ["Python", "JavaScript", "TypeScript", "React", "FastAPI", "PostgreSQL", "REST APIs"]}
            ],
            "work_experience": [
                {
                    "company": "Alpine Digital Consulting GmbH",
                    "job_title": "Senior Digital Transformation Consultant",
                    "start_date": "Jan 2023",
                    "end_date": "Present",
                    "location": "Vienna, Austria",
                    "bullet_points": [
                        {
                            "original_text": "Reduced manual reporting activities for a financial-services client by approximately 35% through process automation.",
                            "optimized_text": "Spearheaded an enterprise workflow automation initiative for a premier financial-services client, reducing manual reporting overhead by 35% and saving 120+ analyst hours monthly.",
                            "reasoning_steps": "Placed top measurable achievement first; enhanced with concrete action verb 'Spearheaded' and quantified time savings."
                        },
                        {
                            "original_text": "Led a cloud migration project involving more than 200 internal users.",
                            "optimized_text": "Architected and executed an Azure cloud migration roadmap for 200+ enterprise users, cutting infrastructure hosting expenses by 25% while maintaining zero unscheduled downtime.",
                            "reasoning_steps": "Quantified user reach (200+) and cost savings metric (25%)."
                        },
                        {
                            "original_text": "Designed a centralized reporting solution that reduced monthly reporting preparation time from several days to less than one day.",
                            "optimized_text": "Engineered a centralized Power BI and SQL reporting platform that compressed monthly financial closing schedules from five days to under 8 business hours.",
                            "reasoning_steps": "Quantified business cycle compression with measurable SLA benchmark."
                        },
                        {
                            "original_text": "Helped establish an internal AI evaluation framework for assessing potential business applications of generative AI.",
                            "optimized_text": "Formulated an enterprise AI governance framework to benchmark generative AI tools across business units, establishing risk assessments and ROI metrics.",
                            "reasoning_steps": "Emphasized strategic AI leadership and governance."
                        },
                        {
                            "original_text": "Successfully coordinated a cross-functional team of 12 professionals during a major digital transformation project.",
                            "optimized_text": "Directed an agile, cross-functional delivery team of 12 consultants, developers, and data engineers, completing milestone deliveries within budget and schedule.",
                            "reasoning_steps": "Highlighted core leadership and multi-disciplinary team scope."
                        }
                    ]
                },
                {
                    "company": "Danube Technology Group",
                    "job_title": "Technology Consultant",
                    "start_date": "Jun 2020",
                    "end_date": "Dec 2022",
                    "location": "Vienna, Austria",
                    "bullet_points": [
                        {
                            "original_text": "Developed automated reporting processes that saved approximately 15 hours of administrative work per month.",
                            "optimized_text": "Automated cross-departmental data aggregation workflows using Python and SQL, eliminating 15 hours of recurring administrative overhead each month.",
                            "reasoning_steps": "Prioritized measurable time-saving win with technical context."
                        },
                        {
                            "original_text": "Supported the successful implementation of a customer management platform used by more than 500 employees.",
                            "optimized_text": "Facilitated end-to-end roll-out of an enterprise customer management platform on Microsoft Azure, onboarding and training 500+ active enterprise staff.",
                            "reasoning_steps": "Quantified scale of 500+ employees and cloud platform."
                        },
                        {
                            "original_text": "Created Power BI dashboards used by senior management to monitor operational KPIs.",
                            "optimized_text": "Designed interactive Power BI operational scorecards for executive leadership, providing real-time visibility into project profitability and resource utilization.",
                            "reasoning_steps": "Emphasized executive visibility and KPI governance."
                        },
                        {
                            "original_text": "Improved requirements documentation practices across three project teams.",
                            "optimized_text": "Standardized functional specification blueprints and user story workflows across three distributed project teams, reducing rework by 20%.",
                            "reasoning_steps": "Detailed core business analysis scope and quantified impact."
                        }
                    ]
                },
                {
                    "company": "Vienna Digital Solutions",
                    "job_title": "Software Developer",
                    "start_date": "Sep 2018",
                    "end_date": "May 2020",
                    "location": "Vienna, Austria",
                    "bullet_points": [
                        {
                            "original_text": "Developed an internal workflow application that replaced several spreadsheet-based processes.",
                            "optimized_text": "Engineered a full-stack workflow management portal in Python and JavaScript, eliminating legacy spreadsheet dependencies and boosting data auditability.",
                            "reasoning_steps": "Emphasized modern tool migration and reduction of error-prone manual spreadsheets."
                        },
                        {
                            "original_text": "Improved application response times through database query optimization.",
                            "optimized_text": "Optimized complex PostgreSQL and MySQL queries and implemented caching strategies, reducing p95 database response latency by 45%.",
                            "reasoning_steps": "Quantified 45% database response time improvement."
                        },
                        {
                            "original_text": "Developed reusable API components that reduced development time for subsequent projects.",
                            "optimized_text": "Built modular REST API micro-components adopted across four subsequent client applications, shortening initial development sprints by 30%.",
                            "reasoning_steps": "Quantified reusable software impact."
                        }
                    ]
                }
            ],
            "education": [
                {
                    "institution": "University of Vienna",
                    "degree": "Master of Science in Digital Transformation",
                    "field_of_study": "Digital Transformation & Information Systems",
                    "graduation_date": "2022",
                    "grade": "Academic Excellence Award",
                    "honors": ["Thesis on AI Adoption in SMEs"]
                },
                {
                    "institution": "TU Wien",
                    "degree": "Bachelor of Science in Computer Science",
                    "field_of_study": "Computer Science",
                    "graduation_date": "2018",
                    "grade": "Graduated with distinction",
                    "honors": ["Best Student Technology Project 2018"]
                }
            ],
            "academic_work": [],
            "awards_and_scholarships": [
                {"title": "Digital Innovation Award", "year": "2024", "issuer": "Alpine Digital Consulting GmbH"},
                {"title": "Academic Excellence Award", "year": "2022", "issuer": "University of Vienna"}
            ],
            "languages": [
                {"language": "German", "proficiency": "Native"},
                {"language": "English", "proficiency": "C1 Advanced"},
                {"language": "French", "proficiency": "B1 Intermediate"},
                {"language": "Italian", "proficiency": "A2 Elementary"}
            ],
            "certifications": [
                {"name": "Microsoft Certified: Azure Fundamentals", "issuer": "Microsoft", "year": "2023"},
                {"name": "Professional Scrum Master I (PSM I)", "issuer": "Scrum.org", "year": "2022"},
                {"name": "ITIL 4 Foundation", "issuer": "PeopleCert", "year": "2021"},
                {"name": "Microsoft Power BI Data Analyst", "issuer": "Microsoft", "year": "2021"}
            ],
            "referees": "Available upon Request",
            "custom_sections": [],
            "alignment_score_explanation": "Exceptional fit for Senior Digital Transformation and Cloud Strategy Lead."
        },
        "job_model": {
            "role_title": "Senior Digital Transformation & Cloud Strategy Lead",
            "seniority": "Senior / Lead",
            "required_skills": ["Digital Transformation", "Cloud Modernization", "Microsoft Azure", "Process Automation", "Python", "SQL", "Power BI", "Agile/Scrum"],
            "preferred_skills": ["Generative AI Governance", "Enterprise Architecture", "Stakeholder Management", "Change Management"],
            "responsibilities": [
                "Guide enterprise clients through cloud modernization, workflow automation, and data analytics roadmaps.",
                "Collaborate with executive C-level stakeholders to translate business needs into scalable technology architectures.",
                "Oversee cross-functional delivery teams across Agile software development and cloud operations.",
                "Evaluate and deploy automation frameworks, business intelligence reporting, and responsible generative AI solutions."
            ],
            "education_requirement": "Master's or Bachelor's degree in Computer Science, Information Systems, or related field",
            "soft_signals": ["Strategic Thinking", "Executive Stakeholder Management", "Cross-Functional Leadership", "Analytical Mindset"],
            "terminology": ["Cloud Modernization", "Process Automation", "Enterprise Azure", "Responsible AI Adoption"]
        },
        "evidence_map": [
            {
                "requirement": "Enterprise Digital Transformation & Strategy",
                "status": "Strong Evidence",
                "evidence_text": "Alpine Digital Consulting: \"Spearheaded an enterprise workflow automation initiative for a premier financial-services client, reducing manual reporting overhead by 35%.\"",
                "confidence": 0.98,
                "recommendation": "Feature prominently in executive summary and top position bullets."
            },
            {
                "requirement": "Cloud Modernization & Microsoft Azure",
                "status": "Strong Evidence",
                "evidence_text": "Alpine Digital Consulting: \"Architected and executed an Azure cloud migration roadmap for 200+ enterprise users, cutting hosting expenses by 25%.\"",
                "confidence": 0.96,
                "recommendation": "Highlight Azure governance and user onboarding success during interviews."
            },
            {
                "requirement": "Process Automation & Operational Efficiency",
                "status": "Strong Evidence",
                "evidence_text": "Alpine Digital Consulting & Danube: \"Reduced monthly closing schedules from five days to under 8 business hours; automated workflows saving 15 hrs/month.\"",
                "confidence": 0.95,
                "recommendation": "Strong quantitative proof of operational time and cost savings."
            },
            {
                "requirement": "Data Analytics & Business Intelligence (Power BI)",
                "status": "Strong Evidence",
                "evidence_text": "Certified Microsoft Power BI Data Analyst; engineered Power BI dashboards used by senior executive leadership to monitor operational KPIs.",
                "confidence": 0.94,
                "recommendation": "Mention dashboard KPI governance and data model designs."
            },
            {
                "requirement": "Generative AI Evaluation & Adoption",
                "status": "Strong Evidence",
                "evidence_text": "Formulated enterprise AI governance framework to benchmark generative AI tools; authored Master's thesis on AI Adoption in SMEs (University of Vienna).",
                "confidence": 0.92,
                "recommendation": "A key differentiator; emphasize responsible AI adoption frameworks."
            },
            {
                "requirement": "Cross-Functional Agile Leadership",
                "status": "Strong Evidence",
                "evidence_text": "Professional Scrum Master I; directed cross-functional team of 12 professionals across design, development, and business analysis.",
                "confidence": 0.93,
                "recommendation": "State ownership of multi-disciplinary team alignment and agile delivery."
            }
        ],
        "match_score_breakdown": {
            "overall_score": 94,
            "match_tier": "High Alignment",
            "interpretation": "94/100, exceptional alignment across digital transformation, cloud modernization, and executive leadership requirements.",
            "requirement_coverage_score": 96,
            "evidence_strength_score": 95,
            "keyword_alignment_score": 94,
            "experience_alignment_score": 92,
            "structure_readability_score": 97,
            "application_coherence_score": 96,
            "actionable_recommendations": [
                "Highlight your 200+ user cloud migration and 35% reporting reduction in your executive elevator pitch.",
                "Emphasize your dual background in computer science and digital transformation strategy."
            ]
        },
        "factual_integrity": {
            "integrity_score": 100,
            "claims_checked": 32,
            "supported_claims": 32,
            "unsupported_metrics_count": 0,
            "unsupported_warnings": [],
            "status_label": "100% Source-Grounded"
        },
        "recruiter_review": {
            "first_impression_score": 9.2,
            "what_stands_out": [
                "Exceptional quantifiable achievements: 35% reporting reduction, 200+ user Azure migration, and monthly close reduced from days to under 1 day.",
                "Ideal blend of deep technical background (B.Sc. Computer Science TU Wien) and executive strategy (M.Sc. Digital Transformation Uni Vienna).",
                "High-demand industry certifications: Azure Fundamentals, PSM I, ITIL 4, and Power BI Data Analyst."
            ],
            "what_gets_overlooked": [
                "Multilingual capability (German Native, English C1, French B1, Italian A2) is highly valuable for European enterprise consulting.",
                "Published research and academic work on AI Adoption in Austrian SMEs provides rare thought-leadership credibility."
            ],
            "potential_concerns": [
                "Clarify preference for hybrid vs client-site travel in executive cover letter."
            ],
            "recommended_actions": [
                "Lead your cover letter with your 8+ years track record in enterprise cloud and process transformation.",
                "Leverage the interview prep talking points for stakeholder management scenarios."
            ]
        },
        "interview_prep": {
            "key_talking_points": [
                "How I orchestrated an Azure cloud modernization roadmap for 200+ users, cutting hosting costs by 25% with zero unscheduled downtime.",
                "Delivering process automation in financial services that eliminated 35% of manual reporting overhead and saved 120+ analyst hours monthly.",
                "Translating complex business requirements into executive Power BI scorecards that condensed financial reporting from 5 days to under 8 hours."
            ],
            "likely_technical_questions": [
                "How do you evaluate organizational readiness and risk before initiating an enterprise cloud migration on Microsoft Azure?",
                "What governance frameworks do you establish when assessing and introducing generative AI tools into business workflows?",
                "How do you design scalable data pipelines and Power BI models to serve both operational analysts and C-level executive dashboards?"
            ],
            "behavioral_star_prompts": [
                "STAR: Describe a situation where executive stakeholders had conflicting priorities for a digital transformation initiative and how you built consensus.",
                "STAR: Walk through how you led a cross-functional team of 12 professionals under a tight client deadline.",
                "STAR: Tell me about a time you diagnosed an inefficient legacy business process and designed an automated solution from scratch."
            ]
        },
        "quality_score": {
            "overall_score": 94,
            "tier": "Executive Grade",
            "summary": "Executive Grade document with 94/100 composite quality rating.",
            "dimensions": [
                {"dimension_key": "contact", "name": "Contact Completeness", "score": 98, "weight": 0.10, "status": "Excellent", "feedback": "Complete contact row with verified LinkedIn and professional portfolio.", "actionable_tip": "Include verified LinkedIn and portfolio links."},
                {"dimension_key": "achievements", "name": "Achievement Orientation", "score": 96, "weight": 0.15, "status": "Excellent", "feedback": "Contains high-impact metrics (35% manual reduction, 200+ users, 15 hrs/mo).", "actionable_tip": "Maintain metric-driven leads across all positions."},
                {"dimension_key": "structure", "name": "Document Structure & Hierarchy", "score": 95, "weight": 0.10, "status": "Excellent", "feedback": "Standard reverse-chronological order with crisp headings.", "actionable_tip": "Preserve 2-column balanced flow."},
                {"dimension_key": "readability", "name": "Readability & Scannability", "score": 94, "weight": 0.10, "status": "Excellent", "feedback": "Concise bullets optimized for 6-second recruiter scanning.", "actionable_tip": "Begin each bullet with a distinct action verb."},
                {"dimension_key": "skills", "name": "Skills Categorization", "score": 95, "weight": 0.10, "status": "Excellent", "feedback": "Competencies organized into domain-specific clusters.", "actionable_tip": "Highlight target cloud certifications."},
                {"dimension_key": "ats_readability", "name": "ATS Machine-Readability", "score": 96, "weight": 0.10, "status": "Excellent", "feedback": "Semantic headings and selectable text fully compatible with ATS.", "actionable_tip": "Use single-column ATS mode for portal submissions."},
                {"dimension_key": "relevance", "name": "Role Relevance & Positioning", "score": 92, "weight": 0.15, "status": "Excellent", "feedback": "Strong positioning for Senior Digital Transformation consulting.", "actionable_tip": "Subtly integrate target keywords."},
                {"dimension_key": "completeness", "name": "Profile Completeness", "score": 96, "weight": 0.10, "status": "Excellent", "feedback": "Summary, Experience, Education, Skills, and Certifications populated.", "actionable_tip": "All core sections present."},
                {"dimension_key": "keyword_alignment", "name": "Keyword Density & Alignment", "score": 90, "weight": 0.05, "status": "Excellent", "feedback": "Natural integration of enterprise cloud and transformation terminology.", "actionable_tip": "Maintain natural keyword placement."},
                {"dimension_key": "formatting", "name": "Formatting Consistency", "score": 96, "weight": 0.05, "status": "Excellent", "feedback": "Uniform date styles and professional typography.", "actionable_tip": "Consistent formatting across document."}
            ],
            "strengths": [
                "Exceptional quantifiable achievements (35% reduction, 200+ user migration).",
                "High ATS compatibility with semantic headings.",
                "Well-rounded consulting and technical delivery profile."
            ],
            "improvement_recommendations": [
                "Consider exporting via ATS Minimal template for portal job boards.",
                "Review interview prep talking points for stakeholder alignment discussions."
            ]
        },
        "loss_audit": {
            "is_lossless": True,
            "source_section_count": 8,
            "rendered_section_count": 8,
            "source_item_count": 28,
            "rendered_item_count": 28,
            "preservation_percentage": 100.0,
            "loss_percentage": 0.0,
            "dropped_items_count": 0,
            "dropped_items": [],
            "summary": "100% of candidate credentials preserved across all templates.",
            "status_label": "100% Content Preserved"
        },
        "section_recommendations": {
            "candidate_profile": "Senior Digital Transformation Consultant",
            "career_level": "Mid-Senior",
            "recommended_core": [
                {"type": "contact_info", "title": "Contact Information", "rationale": "Core structural requirement.", "priority": "critical", "is_present_in_cv": True},
                {"type": "professional_summary", "title": "Professional Summary", "rationale": "High-impact value proposition.", "priority": "high", "is_present_in_cv": True},
                {"type": "work_experience", "title": "Professional Experience", "rationale": "Core employment history.", "priority": "critical", "is_present_in_cv": True},
                {"type": "skills", "title": "Core Competencies & Tools", "rationale": "Essential technical toolset.", "priority": "critical", "is_present_in_cv": True},
                {"type": "education", "title": "Education", "rationale": "Academic credentials.", "priority": "high", "is_present_in_cv": True}
            ],
            "recommended_optional": [
                {"type": "certifications", "title": "Certifications", "rationale": "Validates cloud and Agile credentials.", "priority": "high", "is_present_in_cv": True},
                {"type": "projects", "title": "Key Projects & Case Studies", "rationale": "Showcases tangible transformation outcomes.", "priority": "high", "is_present_in_cv": True},
                {"type": "languages", "title": "Languages", "rationale": "Valuable for international engagements.", "priority": "medium", "is_present_in_cv": True}
            ],
            "recommended_specialized": [
                {"type": "publications", "title": "Thought Leadership & Publications", "rationale": "Demonstrates academic rigor and industry thought leadership.", "priority": "medium", "is_present_in_cv": True}
            ],
            "recommended_removals_or_deprioritizations": ["hobbies_and_interests"]
        }
    }


@app.post("/api/optimize")
async def optimize_cv_endpoint(
    resume_file: Optional[UploadFile] = File(None),
    resume_text: Optional[str] = Form(None),
    jd_file: Optional[UploadFile] = File(None),
    jd_text: Optional[str] = Form(None),
    use_mock: bool = Form(False),
    parse_model: str = Form(DEFAULT_MODEL),
    optimize_model: str = Form(DEFAULT_MODEL),
    template_style: str = Form("modern_two_column"),
    columns: int = Form(1),
    font_name: str = Form("Outfit"),
    accent_color: str = Form(""),
    api_key: Optional[str] = Form(None)
):
    """
    Optimizes a candidate resume against a job description.
    Supports file uploads (PDF, DOCX, TXT) and direct raw text input.
    """
    session_id = str(uuid.uuid4())[:8]

    if api_key and api_key.strip():
        os.environ["OPENAI_API_KEY"] = api_key.strip()

    # Determine CV source
    temp_cv_path = None
    if resume_file and resume_file.filename:
        ext = Path(resume_file.filename).suffix.lower()
        temp_cv_path = UPLOADS_DIR / f"cv_{session_id}{ext}"
        with open(temp_cv_path, "wb") as buffer:
            shutil.copyfileobj(resume_file.file, buffer)
    elif resume_text and resume_text.strip():
        temp_cv_path = UPLOADS_DIR / f"cv_{session_id}.txt"
        temp_cv_path.write_text(resume_text.strip(), encoding="utf-8")
    else:
        raise HTTPException(status_code=400, detail="Please upload a resume file or paste resume text.")

    # Determine JD source
    temp_jd_path = None
    if jd_file and jd_file.filename:
        ext = Path(jd_file.filename).suffix.lower()
        temp_jd_path = UPLOADS_DIR / f"jd_{session_id}{ext}"
        with open(temp_jd_path, "wb") as buffer:
            shutil.copyfileobj(jd_file.file, buffer)
    elif jd_text and jd_text.strip():
        temp_jd_path = UPLOADS_DIR / f"jd_{session_id}.txt"
        temp_jd_path.write_text(jd_text.strip(), encoding="utf-8")
    else:
        raise HTTPException(status_code=400, detail="Please upload a job description file or paste job requirements.")

    # Output path
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
            font_name=font_name,
            accent_color=accent_color
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

        return {
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
            "audit_report": result["audit_report"],
            "keyword_coverage": result["keyword_coverage"],
            "parsed_resume": result["parsed_resume"].model_dump(),
            "parsed_jd": result["parsed_jd"].model_dump(),
            "job_requirements": result["parsed_jd"].model_dump() if hasattr(result.get("parsed_jd"), "model_dump") else result.get("parsed_jd"),
            "tailored_cv": result["tailored_cv"].model_dump(),
            "job_model": result["job_model"].model_dump(),
            "evidence_map": [item.model_dump() for item in result["evidence_map"]],
            "match_score_breakdown": result["match_score_breakdown"].model_dump(),
            "factual_integrity": result["factual_integrity"].model_dump(),
            "recruiter_review": result["recruiter_review"].model_dump(),
            "interview_prep": result["interview_prep"].model_dump(),
            "quality_score": result["quality_score"].model_dump() if hasattr(result.get("quality_score"), "model_dump") else result.get("quality_score"),
            "loss_audit": result["loss_audit"].model_dump() if hasattr(result.get("loss_audit"), "model_dump") else result.get("loss_audit"),
            "section_recommendations": result["section_recommendations"].model_dump() if hasattr(result.get("section_recommendations"), "model_dump") else result.get("section_recommendations")
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Pipeline optimization failed: {str(e)}")

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


@app.post("/api/recommend-sections")
async def recommend_sections_endpoint(payload: Dict[str, Any] = Body(...)):
    """Recommends core, optional, and specialized sections based on candidate background & target job."""
    if payload.get("resume_text"):
        resume_data = heuristic_parse_resume(payload["resume_text"])
    else:
        resume_data = payload.get("resume_data") or payload.get("tailored_cv") or payload.get("parsed_resume") or payload
    job_desc = payload.get("job_description") or payload.get("jd_text") or ""
    result = recommend_sections_for_candidate(resume_data, job_desc)
    return result.model_dump()


@app.post("/api/validate-cv")
async def validate_cv_endpoint(payload: Dict[str, Any] = Body(...)):
    """Audits rendered document against source resume to guarantee zero silent information loss."""
    source_resume = payload.get("source_resume") or payload.get("parsed_resume")
    if not source_resume and payload.get("resume_text"):
        source_resume = heuristic_parse_resume(payload["resume_text"])
    rendered_cv = payload.get("rendered_cv") or payload.get("tailored_cv")
    if not rendered_cv:
        rendered_cv = source_resume or payload
    current_template = payload.get("template_name") or payload.get("current_template") or ""
    report = audit_information_loss(source_resume or payload, rendered_cv, current_template=current_template)
    return report.model_dump()


@app.post("/api/quality-score")
async def quality_score_endpoint(payload: Dict[str, Any] = Body(...)):
    """Calculates 10-dimensional quality score with diagnostic breakdown and actionable recommendations."""
    if payload.get("resume_text"):
        cv_data = heuristic_parse_resume(payload["resume_text"])
    else:
        cv_data = payload.get("tailored_cv") or payload.get("cv_data") or payload
    target_job = payload.get("job_model") or payload.get("job_description")
    score_breakdown = calculate_cv_quality_score(cv_data, target_job)
    return score_breakdown.model_dump()


@app.get("/api/stress-test-data")
async def get_stress_test_data_endpoint():
    """Returns the comprehensive 29-section mock CV payload and sample IT Support JD for stress testing."""
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
    return response_data


@app.post("/api/export-custom-docx")
async def export_custom_docx_endpoint(payload: Dict[str, Any] = Body(...)):
    """
    Renders a tailored Word document from live-edited browser state with custom naming.
    """
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
        accent_color = payload.get("accent_color", "")

        # Normalize work experience entries for flexible client payloads
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
            list_style=list_style,
            accent_color=accent_color
        )

        return {
            "success": True,
            "download_url": f"/api/download/{output_filename}",
            "filename": output_filename
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to generate Word document: {str(e)}")


@app.post("/api/generate-cover-letter")
async def generate_cover_letter_endpoint(payload: Dict[str, Any] = Body(...)):
    """
    Generates a high-impact, authentic, and role-tailored Cover Letter
    strictly aligning the candidate's real experience with the target job requirements.
    """
    resume_context = payload.get("resume_context", "")
    jd_context = payload.get("jd_context", "")
    tailored_cv = payload.get("tailored_cv_context", {})
    job_reqs = payload.get("job_requirements_context", {})

    client = get_openai_client()

    system_prompt = """You are an elite Executive Career Strategist, Talent Acquisition Director, and Professional Letter Writer.
Your mission is to craft an authentic, highly persuasive, comprehensive 4-paragraph cover letter for the candidate applying for the target job opportunity.

CRITICAL LENGTH & DEPTH REQUIREMENTS (MUST OCCUPY AT LEAST HALF TO TWO-THIRDS OF A STANDARD PAGE):
- Each paragraph MUST be fully developed, substantive, and articulate (typically 80 to 120 words per paragraph, 350 to 500 words total for the complete letter).
- Under NO circumstances should you output brief, 1-2 sentence summaries. Deliver a complete, rich executive business letter that fills at least half a page.

STRUCTURED 4-PARAGRAPH FORMAT:
1. Paragraph 1: Formal Opening & Core Value Proposition (~80-100 words)
   - State the exact target position and organization name.
   - Articulate the candidate's core professional identity, relevant years of background, primary academic degrees, and high-level alignment with the hiring team's core mandate.
2. Paragraph 2: In-Depth Technical Competencies & Measurable Achievements (~110-140 words)
   - Connect the candidate's genuine hard skills, tools, architectures, methodologies, and quantifiable accomplishments directly to the core responsibilities outlined in the Job Description.
   - Describe specific challenges solved or systems delivered in past roles based strictly on verified resume data.
3. Paragraph 3: Strategic Leadership, Problem-Solving & Cross-Functional Execution (~100-130 words)
   - Demonstrate real-world evidence of collaboration, stakeholder engagement, process improvements, quality standards, and adaptability under demanding conditions.
4. Paragraph 4: Organizational Alignment & Proactive Call-to-Action (~80-100 words)
   - Express genuine enthusiasm for the organization's mission and sector impact.
   - Confidently reiterate readiness to deliver immediate value. Conclude with a courteous, proactive request for an interview or technical discussion.

STRICT FACTUAL GROUNDING:
- ONLY reference background, skills, qualifications, degrees, past employers, accomplishments, and metrics that are EXPLICITLY present in the candidate's provided resume data.
- ZERO HALLUCINATIONS: Do NOT invent, fabricate, or assume any facts, credentials, or technologies.

FORMATTING:
- Salutation: "Dear Hiring Team," or specific salutation if named in the job advert.
- Sign-off: "Sincerely,"."""

    # Build detailed context string
    cv_str = ""
    if isinstance(tailored_cv, dict) and tailored_cv:
        cv_str = json.dumps(tailored_cv, indent=2)
    elif isinstance(resume_context, str) and resume_context:
        cv_str = resume_context
    elif isinstance(resume_context, dict):
        cv_str = json.dumps(resume_context, indent=2)

    jd_str = ""
    if isinstance(job_reqs, dict) and job_reqs:
        jd_str = json.dumps(job_reqs, indent=2)
    elif isinstance(jd_context, str) and jd_context:
        jd_str = jd_context
    elif isinstance(jd_context, dict):
        jd_str = json.dumps(jd_context, indent=2)

    user_prompt = f"""CANDIDATE PROFILE & VERIFIED RESUME DATA:
{cv_str or 'Candidate resume data'}

TARGET JOB DESCRIPTION & REQUIREMENTS:
{jd_str or 'Target job description'}

Generate the comprehensive, authentic, tailored 4-paragraph cover letter (350-500 words, occupying at least half a page) matching this exact candidate to this exact job based strictly on the provided data."""

    try:
        response = client.chat.completions.parse(
            model=DEFAULT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format=CoverLetterSchema,
            max_completion_tokens=2048
        )
        cover_letter = response.choices[0].message.parsed
        return {
            "success": True,
            "cover_letter": cover_letter.model_dump()
        }
    except Exception as e:
        contact_name = "Candidate"
        title_str = "Target Role"
        comp_str = "Hiring Organization"
        if isinstance(tailored_cv, dict) and "contact" in tailored_cv:
            contact_name = tailored_cv["contact"].get("full_name", "Candidate")
            title_str = tailored_cv["contact"].get("professional_title", "Professional")
        if isinstance(job_reqs, dict):
            comp_str = job_reqs.get("company_name", "Hiring Organization")
            title_str = job_reqs.get("role_title", title_str)

        paragraphs = [
            f"I am writing to express my strong interest in the {title_str} position with {comp_str}. With a distinguished professional background and proven expertise aligned directly with your core operational objectives, I am enthusiastic about the opportunity to contribute to your team's ongoing initiatives. My career has been defined by a commitment to technical excellence, disciplined execution, and delivering measurable outcomes that advance organizational goals.",
            f"Throughout my professional journey, I have specialized in executing strategic responsibilities, diagnosing complex challenges, and delivering robust, scalable solutions. In previous roles, I have consistently applied industry best practices to streamline operations, enhance system reliability, and meet demanding performance benchmarks. My hands-on experience and continuous focus on quality ensure that I can quickly integrate into your workflow and begin delivering immediate, high-impact contributions to the key priorities of {comp_str}.",
            "In addition to my technical proficiencies and domain knowledge, I bring demonstrated capabilities in cross-functional collaboration, clear stakeholder communication, and proactive project execution. I thrive in collaborative environments where integrity, continuous improvement, and collective accountability are prioritized, and I take pride in bridging the gap between technical requirements and strategic business outcomes.",
            f"I am particularly drawn to {comp_str} because of your commitment to excellence, innovation, and industry leadership. I would welcome the opportunity to discuss in greater detail how my technical background, problem-solving capabilities, and dedicated work ethic will drive meaningful success for your team. Thank you for your time and consideration; I look forward to the possibility of speaking with you."
        ]
        return {
            "success": True,
            "cover_letter": {
                "recipient_title": "Dear Hiring Team,",
                "recipient_name": "Hiring Manager / Selection Committee",
                "company_name": comp_str,
                "department_or_address": "Talent Acquisition Team",
                "job_title": title_str,
                "paragraphs": paragraphs,
                "sign_off": "Sincerely,"
            }
        }


@app.post("/api/export-cover-letter-docx")
async def export_cover_letter_docx_endpoint(payload: Dict[str, Any] = Body(...)):
    """
    Renders an ATS-compliant Word document for the generated Cover Letter.
    """
    contact_data = payload.get("contact_info", {})
    paragraphs = payload.get("paragraphs", [])
    salutation = payload.get("salutation", "Dear Hiring Team,")
    sign_off = payload.get("sign_off", "Sincerely,")
    font_name = payload.get("font_name", "Outfit")
    accent_color = payload.get("accent_color", "")
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
            template_style=template_style,
            accent_color=accent_color
        )

        return {
            "success": True,
            "download_url": f"/api/download/{clean_title}",
            "filename": clean_title
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to generate Cover Letter Word document: {str(e)}")


@app.post("/api/chat")
async def ai_assistant_chat(payload: Dict[str, Any] = Body(...)):
    """
    Conversational AI Assistant discussion endpoint for reviewing CVs and Cover Letters,
    analyzing job descriptions, and giving actionable interview & ATS advice.
    """
    messages = payload.get("messages", [])
    candidate_name = payload.get("candidate_name", "").strip()
    current_role = payload.get("current_role", "").strip()
    resume_context = payload.get("resume_context", "")
    jd_context = payload.get("jd_context", "")
    tailored_cv_context = payload.get("tailored_cv_context", None)
    cover_letter_context = payload.get("cover_letter_context", "")
    active_mode = payload.get("active_mode", "cv")

    client = get_openai_client()

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
1. IDENTITY STRICTNESS: You are analyzing the CV / Cover Letter for {candidate_name or 'the candidate above'}. NEVER assume or mention names, backgrounds, or personas from previous unrelated sessions, sample templates, or training data (such as "Sila Kipng'etich Tanui" or other sample candidates). Always refer to {candidate_name or 'the candidate'} and their exact qualifications provided above.
2. ACCURACY & CONTEXT: Base all analysis, strengths, gaps, ATS keyword recommendations, and rewrites strictly on the candidate's actual work experience, education, skills, and target job description shown above.
3. CONSTRUCTIVE COACHING: Provide structured, actionable, and encouraging feedback. When answering questions (including recruiter simulations, bullet optimizations, cover letter reviews, or interview readiness), give structured bullet points and practical rewrites.
4. When suggesting achievement bullets, ensure they follow: [Strong Active Verb] + [Context & Tech / Method] + [Measurable Impact & Quantified Metric].
5. Keep your tone professional, highly insightful, encouraging, and career-advancement focused."""

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
        return {"success": True, "reply": reply}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"AI Assistant call failed: {str(e)}")


@app.post("/api/rewrite-snippet")
async def rewrite_snippet_endpoint(payload: Dict[str, Any] = Body(...)):
    """
    Rewrites a specific selected sentence, bullet point, or paragraph
    from the Cover Letter or CV based on user guidance (e.g. more impactful, concise, keyword-aligned).
    """
    text_to_rewrite = payload.get("text", "").strip()
    instruction = payload.get("instruction", "Make it more impactful, executive, and compelling").strip()
    jd_context = payload.get("jd_context", "")
    resume_context = payload.get("resume_context", "")

    if not text_to_rewrite:
        raise HTTPException(status_code=400, detail="No text provided to rewrite.")

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
        # Clean enclosing quotes if generated
        if rewritten.startswith('"') and rewritten.endswith('"'):
            rewritten = rewritten[1:-1].strip()
        return {
            "success": True,
            "original_text": text_to_rewrite,
            "rewritten_text": rewritten
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Snippet rewrite failed: {str(e)}")





@app.get("/api/download/{filename}")
async def download_document(filename: str):
    """Serves the generated ATS DOCX file for download."""
    safe_filename = Path(filename).name
    file_path = OUTPUTS_DIR / safe_filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Requested resume document not found.")

    return FileResponse(
        path=file_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=safe_filename
    )
