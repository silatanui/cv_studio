"""
test_stress_cv.py
Comprehensive test suite for 29-section stress test CV, dynamic section engine,
10-dimensional quality rubric, information loss audit, and dedicated ATS template.
"""

import unittest
from schemas import ResumeSchema, TailoredResumeSchema
from mock_stress_data import DR_ELENA_VANCE_STRESS_RESUME, SAMPLE_IT_SUPPORT_JD
from optimizer import (
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
    detect_candidate_profile,
    CORE_SECTIONS,
    COMMON_OPTIONAL_SECTIONS
)
from pathlib import Path
from renderer import build_ats_friendly_docx
from fastapi.testclient import TestClient
from app import app


class TestStressCV(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_heuristic_parse_29_section_cv(self):
        """Test parsing of the 29-section comprehensive stress CV."""
        parsed = heuristic_parse_resume(DR_ELENA_VANCE_STRESS_RESUME)
        self.assertIsInstance(parsed, ResumeSchema)
        self.assertEqual(parsed.contact.full_name, "Dr. Elena Vance")
        self.assertTrue(len(parsed.work_experience) >= 2)
        self.assertTrue(len(parsed.education) >= 2)
        self.assertTrue(len(parsed.skills) >= 5)

        # Dynamic sections
        self.assertTrue(hasattr(parsed, "sections"))
        self.assertTrue(len(parsed.sections) > 10, f"Expected >10 dynamic sections, got {len(parsed.sections)}")

        # Check specific recognized canonical section types
        canonical_types = [s.canonical_type for s in parsed.sections]
        self.assertIn("publications", canonical_types)
        self.assertIn("research_experience", canonical_types)
        self.assertIn("teaching_experience", canonical_types)
        self.assertIn("speaking_engagements", canonical_types)
        self.assertIn("leadership_experience", canonical_types)
        self.assertIn("portfolio", canonical_types)

    def test_information_loss_audit_zero_dropped(self):
        """Verify that audit_information_loss detects zero dropped items when all sections are rendered."""
        parsed = heuristic_parse_resume(DR_ELENA_VANCE_STRESS_RESUME)
        job_reqs = parse_job_description(SAMPLE_IT_SUPPORT_JD)
        tailored = mock_optimize_pipeline(parsed, job_reqs)

        loss_report = audit_information_loss(parsed, tailored, current_template="template_ats_minimal")
        self.assertEqual(loss_report.dropped_items_count, 0)
        self.assertEqual(loss_report.loss_percentage, 0.0)
        self.assertIn("100% of candidate credentials preserved", loss_report.summary)

    def test_cv_quality_score_10_dimensions(self):
        """Verify that calculate_cv_quality_score evaluates all 10 rubric dimensions."""
        parsed = heuristic_parse_resume(DR_ELENA_VANCE_STRESS_RESUME)
        quality = calculate_cv_quality_score(parsed)

        self.assertTrue(quality.overall_score >= 80, f"Expected high score for comprehensive CV, got {quality.overall_score}")
        self.assertEqual(len(quality.dimensions), 10)

        dimension_names = [d.dimension_key for d in quality.dimensions]
        expected_dims = [
            "contact", "achievements", "structure", "readability",
            "skills", "ats_readability", "relevance", "completeness",
            "keyword_alignment", "formatting"
        ]
        for dim in expected_dims:
            self.assertIn(dim, dimension_names)

        # Check that scores are bounded
        for d in quality.dimensions:
            self.assertGreaterEqual(d.score, 0.0)
            self.assertLessEqual(d.score, d.max_score)

    def test_ai_section_recommendations_and_candidate_profile(self):
        """Verify candidate profile detection and tailored section recommendations."""
        parsed = heuristic_parse_resume(DR_ELENA_VANCE_STRESS_RESUME)
        profile = detect_candidate_profile(parsed)
        self.assertIn("Academic", profile[1])

        recommendations = recommend_sections_for_candidate(parsed)
        self.assertTrue(len(recommendations.recommended_sections) >= 3)
        rec_types = [r.section_type for r in recommendations.recommended_sections]
        self.assertTrue(any(t in rec_types for t in ["publications", "research_experience", "grants_funding"]))

    def test_evidence_map_respectful_gap_wording(self):
        """Verify that IT Support JD matching produces respectful gap phrasing ('Not found in the CV')."""
        parsed = heuristic_parse_resume(DR_ELENA_VANCE_STRESS_RESUME)
        job_model = extract_structured_job_model(SAMPLE_IT_SUPPORT_JD)
        evidence_items = heuristic_generate_evidence_map(parsed, job_model)
        self.assertTrue(len(evidence_items) > 0)

        for item in evidence_items:
            if "No Evidence" in item.status:
                # Ensure phrasing is respectful and accurate
                self.assertIn("Not found in the CV", item.evidence_text)

    def test_docx_rendering_with_ats_minimal_and_visual_template(self):
        """Test DOCX export with both template_ats_minimal and visual template on 29-section CV."""
        parsed = heuristic_parse_resume(DR_ELENA_VANCE_STRESS_RESUME)
        job_reqs = parse_job_description(SAMPLE_IT_SUPPORT_JD)
        tailored = mock_optimize_pipeline(parsed, job_reqs)

        temp_dir = Path("outputs")
        temp_dir.mkdir(exist_ok=True)
        out_ats = temp_dir / "test_stress_ats.docx"
        out_vis = temp_dir / "test_stress_vis.docx"

        # 1. ATS Minimal DOCX
        saved_ats = build_ats_friendly_docx(
            data=tailored,
            contact_info=parsed.contact,
            output_path=out_ats,
            template_style="template_ats_minimal",
            columns=1
        )
        self.assertTrue(Path(saved_ats).exists())
        self.assertTrue(Path(saved_ats).stat().st_size > 5000)

        # 2. Modern Two-Column Visual DOCX
        saved_vis = build_ats_friendly_docx(
            data=tailored,
            contact_info=parsed.contact,
            output_path=out_vis,
            template_style="template_2_teal",
            columns=2
        )
        self.assertTrue(Path(saved_vis).exists())
        self.assertTrue(Path(saved_vis).stat().st_size > 5000)

    def test_api_endpoints_stress_test_and_quality(self):
        """Verify new REST endpoints: /api/stress-test-data, /api/quality-score, /api/validate-cv."""
        # 1. GET /api/stress-test-data
        res_stress = self.client.get("/api/stress-test-data")
        self.assertEqual(res_stress.status_code, 200)
        data_stress = res_stress.json()
        self.assertIn("resume_text", data_stress)
        self.assertIn("tailored_cv", data_stress)
        self.assertIn("quality_score", data_stress)
        self.assertIn("loss_audit", data_stress)
        self.assertIn("section_recommendations", data_stress)
        self.assertEqual(data_stress["loss_audit"]["dropped_items_count"], 0)

        # 2. POST /api/quality-score
        res_qual = self.client.post("/api/quality-score", json={"resume_text": DR_ELENA_VANCE_STRESS_RESUME})
        self.assertEqual(res_qual.status_code, 200)
        data_qual = res_qual.json()
        self.assertIn("overall_score", data_qual)
        self.assertEqual(len(data_qual["dimensions"]), 10)

        # 3. POST /api/validate-cv
        res_val = self.client.post("/api/validate-cv", json={
            "resume_text": DR_ELENA_VANCE_STRESS_RESUME,
            "template_name": "template_ats_minimal"
        })
        self.assertEqual(res_val.status_code, 200)
        data_val = res_val.json()
        self.assertEqual(data_val["dropped_items_count"], 0)
        self.assertEqual(data_val["loss_percentage"], 0.0)

        # 4. POST /api/recommend-sections
        res_rec = self.client.post("/api/recommend-sections", json={"resume_text": DR_ELENA_VANCE_STRESS_RESUME})
        self.assertEqual(res_rec.status_code, 200)
        data_rec = res_rec.json()
        self.assertIn("detected_profile", data_rec)
        self.assertIn("recommended_sections", data_rec)


if __name__ == "__main__":
    unittest.main()
