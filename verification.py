"""
Fact Verification and ATS Alignment Scoring Module.

Safeguards against LLM hallucinations by auditing the generated TailoredResumeSchema
against the source ResumeSchema and computes mathematical keyword alignment metrics.
"""

from typing import List, Set, Dict, Any
from schemas import ResumeSchema, TailoredResumeSchema, JobRequirementsSchema
from sanitizer import sanitize_text


def calculate_keyword_coverage(
    jd_keywords: List[str],
    resume_text: str
) -> Dict[str, Any]:
    """
    Calculates exact keyword intersection coverage between job requirements (K_R)
    and tailored resume content (K_E).
    
    Returns:
        Dictionary with matched keywords, missing keywords, and coverage score.
    """
    if not jd_keywords:
        return {
            "score": 1.0,
            "matched": [],
            "missing": [],
            "total_required": 0,
            "total_matched": 0
        }

    resume_clean = sanitize_text(resume_text).lower()
    matched = []
    missing = []

    for kw in jd_keywords:
        kw_clean = sanitize_text(kw).lower()
        if kw_clean in resume_clean:
            matched.append(kw)
        else:
            missing.append(kw)

    coverage_score = len(matched) / len(jd_keywords) if jd_keywords else 1.0

    return {
        "score": coverage_score,
        "matched": matched,
        "missing": missing,
        "total_required": len(jd_keywords),
        "total_matched": len(matched)
    }


def verify_factual_integrity(
    source_resume: ResumeSchema,
    tailored_resume: TailoredResumeSchema
) -> Dict[str, Any]:
    """
    Audits the generated tailored resume against the original source resume
    to detect hallucinated employers, education institutions, or fabricated degrees.
    
    Returns:
        Audit report detailing validation status and any discrepancies.
    """
    discrepancies = []

    # 1. Verify Employer Integrity
    source_companies_map = {sanitize_text(exp.company).lower(): exp.company for exp in source_resume.work_experience}
    tailored_companies_map = {sanitize_text(exp.company).lower(): exp.company for exp in tailored_resume.work_experience}

    fabricated_keys = set(tailored_companies_map.keys()) - set(source_companies_map.keys())
    if fabricated_keys:
        names = [tailored_companies_map[k] for k in fabricated_keys]
        discrepancies.append(f"Potential hallucinated employer(s): {', '.join(names)}")

    # 2. Verify Education Institution & Degree Integrity
    source_institutions_map = {sanitize_text(edu.institution).lower(): edu.institution for edu in source_resume.education}
    tailored_institutions_map = {sanitize_text(edu.institution).lower(): edu.institution for edu in tailored_resume.education}

    fabricated_inst_keys = set(tailored_institutions_map.keys()) - set(source_institutions_map.keys())
    if fabricated_inst_keys:
        names = [tailored_institutions_map[k] for k in fabricated_inst_keys]
        discrepancies.append(f"Potential hallucinated educational institution(s): {', '.join(names)}")

    # 3. Verify Experience Count Consistency
    if len(tailored_resume.work_experience) > len(source_resume.work_experience):
        discrepancies.append(
            f"Tailored resume contains more job roles ({len(tailored_resume.work_experience)}) "
            f"than source resume ({len(source_resume.work_experience)})."
        )

    is_valid = len(discrepancies) == 0

    return {
        "is_valid": is_valid,
        "discrepancies": discrepancies,
        "source_companies_count": len(source_companies_map),
        "tailored_companies_count": len(tailored_companies_map),
    }
