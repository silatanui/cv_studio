"""
Test Suite for Algorithmic CV Optimization Architecture.

Tests schema contracts, sanitization, document rendering,
fact auditing, and end-to-end pipeline execution.
"""

import sys
import unittest
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent))

from schemas import (
    ContactInformation,
    WorkExperience,
    Education,
    ResumeSchema,
    JobRequirementsSchema,
    OptimizedBullet,
    OptimizedWorkExperience,
    TailoredResumeSchema,
)
from sanitizer import sanitize_text, sanitize_list
from extractor import extract_text_from_file
from renderer import build_ats_friendly_docx
from verification import verify_factual_integrity, calculate_keyword_coverage
from pipeline import run_cv_optimization_pipeline


class TestCVOptimizer(unittest.TestCase):

    def test_sanitizer(self):
        """Test replacement of non-standard typography and quotes."""
        raw_text = '“Smart quotes” and ‘single quotes’ — with em–dashes • bullets \u2026'
        clean = sanitize_text(raw_text)
        self.assertNotIn('“', clean)
        self.assertNotIn('”', clean)
        self.assertNotIn('‘', clean)
        self.assertNotIn('’', clean)
        self.assertNotIn('—', clean)
        self.assertNotIn('•', clean)
        self.assertIn('"', clean)
        self.assertIn("'", clean)
        self.assertIn("-", clean)

    def test_schemas(self):
        """Test Pydantic model validation and serialization."""
        contact = ContactInformation(
            full_name="Jane Doe",
            email="jane@example.com",
            phone="123-456-7890"
        )
        resume = ResumeSchema(
            contact=contact,
            summary="Experienced Engineer",
            skills=["Python", "FastAPI"]
        )
        self.assertEqual(resume.contact.full_name, "Jane Doe")
        self.assertEqual(len(resume.skills), 2)
        json_data = resume.model_dump_json()
        self.assertIn("Jane Doe", json_data)

    def test_docx_rendering(self):
        """Test ATS-compliant DOCX generation."""
        contact = ContactInformation(
            full_name="Jane Doe",
            email="jane@example.com",
            phone="123-456-7890",
            location="New York, NY",
            linkedin_url="linkedin.com/in/janedoe"
        )
        tailored = TailoredResumeSchema(
            contact=contact,
            professional_summary="Accomplished Engineer with high impact.",
            skills_section=["Python", "AWS", "FastAPI"],
            work_experience=[
                OptimizedWorkExperience(
                    company="Tech Corp",
                    job_title="Lead Engineer",
                    start_date="2020",
                    end_date="Present",
                    bullet_points=[
                        OptimizedBullet(
                            reasoning_steps="Reframed with metrics.",
                            original_text="Built APIs.",
                            optimized_text="Architected high-throughput REST APIs handling 10M daily requests with 99.9% uptime."
                        )
                    ]
                )
            ],
            education=[
                Education(
                    institution="MIT",
                    degree="B.S.",
                    field_of_study="Computer Science",
                    graduation_date="2020"
                )
            ]
        )
        out_path = Path(__file__).parent / "test_output.docx"
        saved = build_ats_friendly_docx(tailored, contact, out_path)
        self.assertTrue(saved.exists())
        self.assertGreater(saved.stat().st_size, 1000)

        # Cleanup test doc
        if saved.exists():
            saved.unlink()

    def test_verification_and_coverage(self):
        """Test anti-hallucination auditor and keyword coverage calculation."""
        contact = ContactInformation(full_name="A", email="a@b.com")
        source = ResumeSchema(
            contact=contact,
            work_experience=[
                WorkExperience(company="Acme Corp", job_title="Dev", start_date="2020", end_date="2021")
            ],
            education=[
                Education(institution="State Univ", degree="B.S.", field_of_study="CS", graduation_date="2020")
            ]
        )
        tailored_valid = TailoredResumeSchema(
            contact=contact,
            professional_summary="Dev at Acme Corp",
            work_experience=[
                OptimizedWorkExperience(company="Acme Corp", job_title="Dev", start_date="2020", end_date="2021")
            ],
            education=[
                Education(institution="State Univ", degree="B.S.", field_of_study="CS", graduation_date="2020")
            ]
        )
        audit_valid = verify_factual_integrity(source, tailored_valid)
        self.assertTrue(audit_valid["is_valid"])

        # Test with hallucinated company
        tailored_invalid = TailoredResumeSchema(
            contact=contact,
            professional_summary="Dev at Google",
            work_experience=[
                OptimizedWorkExperience(company="Google", job_title="VP", start_date="2020", end_date="2021")
            ],
            education=[]
        )
        audit_invalid = verify_factual_integrity(source, tailored_invalid)
        self.assertFalse(audit_invalid["is_valid"])
        self.assertIn("Google", audit_invalid["discrepancies"][0])

        # Test keyword coverage
        keywords = ["Python", "FastAPI", "Kubernetes", "AWS"]
        text = "Experienced in Python and FastAPI backend development on AWS."
        cov = calculate_keyword_coverage(keywords, text)
        self.assertEqual(cov["total_matched"], 3)
        self.assertEqual(cov["score"], 0.75)
        self.assertIn("Kubernetes", cov["missing"])

    def test_end_to_end_pipeline_mock(self):
        """Test full pipeline execution in mock mode."""
        base_dir = Path(__file__).parent
        cv_path = base_dir / "sample_data" / "sample_resume.txt"
        jd_path = base_dir / "sample_data" / "job_description.txt"
        out_path = base_dir / "test_pipeline_result.docx"

        result = run_cv_optimization_pipeline(
            input_cv_path=str(cv_path),
            input_jd_path=str(jd_path),
            output_docx_path=str(out_path),
            use_mock=True
        )

        self.assertTrue(Path(result["output_path"]).exists())
        self.assertTrue(result["audit_report"]["is_valid"])
        self.assertGreater(result["keyword_coverage"]["score"], 0.0)

        # Cleanup
        if out_path.exists():
            out_path.unlink()


if __name__ == "__main__":
    unittest.main()
