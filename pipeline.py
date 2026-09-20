"""
End-to-End CV Optimization Pipeline.

Coordinates document ingestion, schema normalization, LLM-based strategic reframing,
anti-hallucination verification, and ATS-compliant DOCX document synthesis.
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

from extractor import extract_text_from_file
from optimizer import (
    parse_resume_to_schema,
    parse_job_description,
    optimize_cv,
    mock_optimize_pipeline,
    extract_structured_job_model,
    generate_evidence_map,
    calculate_job_match_score,
    audit_factual_integrity,
    generate_recruiter_review,
    generate_interview_prep,
)
from verification import verify_factual_integrity, calculate_keyword_coverage
from renderer import build_ats_friendly_docx
from schemas import ResumeSchema, JobRequirementsSchema, TailoredResumeSchema
from section_engine import (
    calculate_cv_quality_score,
    audit_information_loss,
    recommend_sections_for_candidate,
)


def run_cv_optimization_pipeline(
    input_cv_path: str,
    input_jd_path: str,
    output_docx_path: str,
    use_mock: bool = False,
    parse_model: str = "gpt-4o-mini",
    optimize_model: str = "gpt-4o-mini",
    template_style: str = "modern_two_column",
    columns: int = 1,
    font_name: str = "Outfit",
    accent_color: str = ""
) -> Dict[str, Any]:
    """
    Executes the complete 4-stage CV optimization and generation pipeline.
    
    Args:
        input_cv_path: Path to candidate resume (PDF, DOCX, TXT).
        input_jd_path: Path to target job description (TXT, DOCX, PDF).
        output_docx_path: Destination path for generated ATS DOCX.
        use_mock: If True, uses offline mock logic without calling OpenAI API.
        parse_model: OpenAI model for schema parsing.
        optimize_model: OpenAI model for strategic reframing.
        
    Returns:
        Dictionary containing execution summary, metrics, intelligence models, and file output path.
    """
    print("=" * 60)
    print("STARTING ALGORITHMIC CV OPTIMIZATION PIPELINE")
    print("=" * 60)

    # Stage 1: Ingestion & Extraction
    print("\n[1/4] Ingesting source resume and job description...")
    raw_cv = extract_text_from_file(input_cv_path)
    raw_jd = extract_text_from_file(input_jd_path)
    print(f"      - Source Resume: {len(raw_cv)} characters extracted.")
    print(f"      - Job Description: {len(raw_jd)} characters extracted.")

    # Stage 2: Schema Normalization & Structured Job Intelligence
    print("\n[2/4] Normalizing data into canonical Pydantic models...")
    if use_mock:
        from optimizer import heuristic_parse_resume, heuristic_parse_jd, heuristic_extract_job_model
        parsed_resume = heuristic_parse_resume(raw_cv) if len(raw_cv) > 30 else parse_resume_to_schema(raw_cv)
        parsed_jd = heuristic_parse_jd(raw_jd) if len(raw_jd) > 20 else parse_job_description(raw_jd)
        job_model = heuristic_extract_job_model(raw_jd)
    else:
        parsed_resume = parse_resume_to_schema(raw_cv, model=parse_model)
        parsed_jd = parse_job_description(raw_jd, model=parse_model)
        job_model = extract_structured_job_model(raw_jd, model=parse_model)

    print(f"      - Candidate: {parsed_resume.contact.full_name}")
    print(f"      - Target Role: {parsed_jd.job_title} at {parsed_jd.company_name or 'Target Company'}")
    print(f"      - Priority Keywords ({len(parsed_jd.priority_keywords)}): {', '.join(parsed_jd.priority_keywords[:5])}...")

    # Stage 3: Strategic Reframing, Evidence Mapping & Verification
    print("\n[3/4] Optimizing CV content for ATS compatibility and keyword alignment...")
    if use_mock:
        tailored_cv = mock_optimize_pipeline(parsed_resume, parsed_jd)
    else:
        tailored_cv = optimize_cv(parsed_resume, parsed_jd, model=optimize_model)

    # Evidence Mapping & Factual Integrity Verification
    if use_mock:
        from optimizer import heuristic_generate_evidence_map, heuristic_recruiter_review, heuristic_interview_prep
        evidence_map = heuristic_generate_evidence_map(parsed_resume, job_model)
        match_score_breakdown = calculate_job_match_score(parsed_resume, job_model, evidence_map)
        factual_integrity_report = audit_factual_integrity(parsed_resume, tailored_cv)
        recruiter_review = heuristic_recruiter_review(tailored_cv, job_model)
        interview_prep = heuristic_interview_prep(tailored_cv, job_model)
    else:
        evidence_map = generate_evidence_map(parsed_resume, job_model, model=optimize_model)
        match_score_breakdown = calculate_job_match_score(parsed_resume, job_model, evidence_map)
        factual_integrity_report = audit_factual_integrity(parsed_resume, tailored_cv)
        recruiter_review = generate_recruiter_review(parsed_resume, tailored_cv, job_model, model=optimize_model)
        interview_prep = generate_interview_prep(tailored_cv, job_model, model=optimize_model)

    audit_report = verify_factual_integrity(parsed_resume, tailored_cv)
    status_str = "[PASSED]" if audit_report['is_valid'] else "[WARNING]"
    print(f"      - Fact Audit Status: {status_str}")
    print(f"      - Factual Integrity Score: {factual_integrity_report.integrity_score}% ({factual_integrity_report.status_label})")
    print(f"      - Job Match Score: {match_score_breakdown.overall_score}/100 ({match_score_breakdown.match_tier})")

    # Keyword Coverage Metrics
    all_tailored_text = tailored_cv.professional_summary + " " + " ".join(tailored_cv.skills_section)
    for exp in tailored_cv.work_experience:
        all_tailored_text += " " + " ".join([b.optimized_text for b in exp.bullet_points])
    
    coverage = calculate_keyword_coverage(parsed_jd.priority_keywords, all_tailored_text)
    total_matched = coverage.get('total_matched', len(coverage.get('matched', [])))
    total_required = coverage.get('total_required', len(parsed_jd.priority_keywords))
    score_val = coverage.get('score', 1.0)
    print(f"      - ATS Keyword Match Coverage: {score_val * 100:.1f}% ({total_matched}/{total_required} keywords)")

    # Stage 4: Layout Synthesis & Rendering
    print("\n[4/4] Rendering final ATS-compliant Word document...")
    saved_doc_path = build_ats_friendly_docx(
        data=tailored_cv,
        contact_info=parsed_resume.contact,
        output_path=output_docx_path,
        template_style=template_style,
        columns=columns,
        font_name=font_name,
        accent_color=accent_color
    )
    print(f"      - File successfully saved: {saved_doc_path}")

    print("\n" + "=" * 60)
    print(f"[PIPELINE COMPLETE] Generated tailored resume at '{saved_doc_path}'")
    print("=" * 60)

    # Dynamic Quality Scoring, Information Loss Audit & Section Recommendations
    quality_score = calculate_cv_quality_score(tailored_cv, job_model)
    loss_audit = audit_information_loss(parsed_resume, tailored_cv)
    section_recs = recommend_sections_for_candidate(tailored_cv, raw_jd)

    return {
        "output_path": str(saved_doc_path),
        "audit_report": audit_report,
        "keyword_coverage": coverage,
        "parsed_resume": parsed_resume,
        "tailored_cv": tailored_cv,
        "parsed_jd": parsed_jd,
        "job_model": job_model,
        "evidence_map": evidence_map,
        "match_score_breakdown": match_score_breakdown,
        "factual_integrity": factual_integrity_report,
        "recruiter_review": recruiter_review,
        "interview_prep": interview_prep,
        "quality_score": quality_score,
        "loss_audit": loss_audit,
        "section_recommendations": section_recs
    }


if __name__ == "__main__":
    base_dir = Path(__file__).parent
    cv_sample = base_dir / "sample_data" / "sample_resume.txt"
    jd_sample = base_dir / "sample_data" / "job_description.txt"
    output_docx = base_dir / "Tailored_ATS_Resume.docx"

    run_cv_optimization_pipeline(
        input_cv_path=str(cv_sample),
        input_jd_path=str(jd_sample),
        output_docx_path=str(output_docx)
    )
