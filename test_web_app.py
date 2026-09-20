"""
Test Suite for FastAPI Web Application Endpoints with Template & Export Support.
"""

import sys
import unittest
from pathlib import Path
from fastapi.testclient import TestClient

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent))

from app import app, OUTPUTS_DIR


class TestWebApp(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_serve_index(self):
        """Test GET / renders HTML dashboard."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers["content-type"])
        self.assertIn("Candidate Master Resume", response.text)
        self.assertIn("viewInputStudio", response.text)

    def test_health_check(self):
        """Test GET /api/health endpoint."""
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["model"], "gpt-4o-mini")

    def test_sample_data(self):
        """Test GET /api/sample-data returns valid text."""
        response = self.client.get("/api/sample-data")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("SOFIA KATHARINA BERGER", data["resume_text"])
        self.assertIn("Senior Digital Transformation", data["job_description_text"])

    def test_optimize_endpoint(self):
        """Test POST /api/optimize with text form data in mock mode."""
        payload = {
            "resume_text": "Sila Kipngetich Tanui\nSystems Engineer\nSkills: C, C++, Linux",
            "jd_text": "Requirements: Systems Software Engineer with C++ and Linux internals.",
            "use_mock": "true",
            "template_style": "modern_two_column",
            "columns": "2",
            "font_name": "Outfit"
        }
        response = self.client.post("/api/optimize", data=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertIn("download_url", data)
        self.assertIn("Tailored_ATS_Resume", data["filename"])
        self.assertTrue(data["audit_report"]["is_valid"])

    def test_export_custom_docx_endpoint(self):
        """Test POST /api/export-custom-docx endpoint with 2-column Outfit and Abadi."""
        payload = {
            "contact_info": {
                "full_name": "Sila Kipngetich Tanui",
                "professional_title": "Systems Software Engineer",
                "email": "silatanuikipngetich@gmail.com",
                "phone": "+362032336",
                "location": "Debrecen, Hungary",
                "linkedin_url": "https://linkedin.com/in/tanui-kipngetich-sila"
            },
            "tailored_cv": {
                "professional_summary": "MSc Computer Science graduate specializing in low-level systems and OS internals.",
                "skills_section": ["C", "C++", "Linux", "Python", "ARM Architecture"],
                "work_experience": [
                    {
                        "company": "Transcosmos (Fossil Group)",
                        "job_title": "Customer Success Specialist",
                        "start_date": "Oct 2025",
                        "end_date": "Feb 2026",
                        "location": "Debrecen, Hungary",
                        "bullet_points": [
                            {
                                "reasoning_steps": "Targeted enterprise workflows",
                                "original_text": "Maintained CSAT above 90%",
                                "optimized_text": "Maintained customer satisfaction (CSAT) score above 90% resolving technical transactions."
                            }
                        ]
                    }
                ],
                "education": [
                    {
                        "institution": "University of Debrecen",
                        "degree": "MSc Computer Science",
                        "field_of_study": "Systems Software",
                        "graduation_date": "2024 - 2026",
                        "grade": "Final grade: 4.39/5.00"
                    }
                ],
                "referees": "Available upon Request"
            },
            "template_style": "modern_two_column",
            "columns": 2,
            "font_name": "Outfit"
        }

        response = self.client.post("/api/export-custom-docx", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertIn("download_url", data)

        # Test download of custom DOCX
        dl_res = self.client.get(data["download_url"])
        self.assertEqual(dl_res.status_code, 200)
        self.assertGreater(len(dl_res.content), 1000)

        # Test with Abadi font & 1 Column
        payload["font_name"] = "Abadi"
        payload["columns"] = 1
        payload["template_style"] = "classic_single_column"
        response2 = self.client.post("/api/export-custom-docx", json=payload)
        self.assertEqual(response2.status_code, 200)
        data2 = response2.json()
        self.assertTrue(data2["success"])

    def test_export_template_4_banner(self):
        """Test POST /api/export-custom-docx endpoint with Template 4 Shaded Banner."""
        payload = {
            "contact_info": {
                "full_name": "Olivia Sanchez",
                "professional_title": "Administrative Manager",
                "email": "hello@reallygreatsite.com",
                "phone": "123-456-7890",
                "location": "123 Anywhere St., Any City"
            },
            "tailored_cv": {
                "professional_summary": "Detail-oriented administrative professional with over three years of experience.",
                "skills_section": ["Client Acquisition", "B2B Sales", "Negotiation", "Problem-Solving", "Time Management", "Market Analysis"],
                "work_experience": [
                    {
                        "company": "Arowwai Industries",
                        "job_title": "Administrative Assistant",
                        "start_date": "Oct 2023",
                        "end_date": "Present",
                        "bullet_points": [
                            {"reasoning_steps": "Coordination", "original_text": "Managed calendars", "optimized_text": "Managed executive calendars, schedule meetings, and coordinate travel arrangements."}
                        ]
                    }
                ],
                "education": [
                    {
                        "institution": "University of Business Excellence",
                        "degree": "Bachelor of Business Administration",
                        "field_of_study": "International Business",
                        "graduation_date": "Jan 2019 - Feb 2021"
                    }
                ]
            },
            "template_style": "template_4_banner",
            "columns": 1,
            "font_name": "Outfit"
        }

        response = self.client.post("/api/export-custom-docx", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        dl_res = self.client.get(data["download_url"])
        self.assertEqual(dl_res.status_code, 200)
        self.assertGreater(len(dl_res.content), 1000)

    def test_export_template_3_navy(self):
        """Test POST /api/export-custom-docx endpoint with Template 3 Navy."""
        payload = {
            "contact_info": {"full_name": "Test User", "professional_title": "Dev", "email": "test@example.com", "phone": "123", "location": "Test City"},
            "tailored_cv": {"professional_summary": "Summary", "skills_section": ["A"], "work_experience": [], "education": []},
            "template_style": "template_3_navy",
            "columns": 1,
            "font_name": "Outfit"
        }
        response = self.client.post("/api/export-custom-docx", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])

    def test_generate_cover_letter_endpoint(self):
        """Test POST /api/generate-cover-letter endpoint."""
        payload = {
            "resume_context": "Sila Kipngetich Tanui\nSystems Software Engineer\nMSc Computer Science\nSkills: C, C++, Linux",
            "jd_context": "Software Engineer in CE-SW group at Arm. Requires C/C++, OS, debugging.",
            "tailored_cv_context": {
                "contact": {"full_name": "Sila Kipngetich Tanui", "professional_title": "Systems Software Engineer"}
            }
        }
        response = self.client.post("/api/generate-cover-letter", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertIn("cover_letter", data)
        self.assertGreater(len(data["cover_letter"]["paragraphs"]), 0)

    def test_export_cover_letter_docx_endpoint(self):
        """Test POST /api/export-cover-letter-docx endpoint."""
        payload = {
            "contact_info": {
                "full_name": "Sila Kipngetich Tanui",
                "email": "silatanuikipngetich@gmail.com",
                "phone": "+36 20 323 3673",
                "location": "Debrecen, Hungary",
                "portfolio_url": "tanuisila.dev"
            },
            "paragraphs": [
                "I am writing to apply for the Software Engineer position in the CE-SW group at Arm.",
                "During my studies, I developed a strong foundation in C and C++ programming languages.",
                "Moreover, I have experience in roles that involve communicating highly technical details to others.",
                "Most importantly, what attracts me to working at Arm is the ability to work with modern hardware."
            ],
            "salutation": "Dear Hiring Team,",
            "sign_off": "Sincerely,",
            "font_name": "Outfit",
            "doc_title": "Sila_Tanui_Cover_Letter"
        }
        response = self.client.post("/api/export-cover-letter-docx", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertIn("Sila_Tanui_Cover_Letter.docx", data["filename"])
        dl_res = self.client.get(data["download_url"])
        self.assertEqual(dl_res.status_code, 200)
        self.assertGreater(len(dl_res.content), 1000)

    def test_export_custom_docx_with_custom_title(self):
        """Test POST /api/export-custom-docx endpoint with custom document title."""
        payload = {
            "contact_info": {"full_name": "Sila Kipngetich Tanui", "professional_title": "Systems Software Engineer", "email": "sila@example.com"},
            "tailored_cv": {"professional_summary": "Summary", "skills_section": ["C++", "Linux"], "work_experience": [], "education": []},
            "template_style": "template_1_blue",
            "columns": 1,
            "font_name": "Outfit",
            "doc_title": "My_Custom_Targeted_Resume"
        }
        response = self.client.post("/api/export-custom-docx", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertIn("My_Custom_Targeted_Resume.docx", data["filename"])

    def test_ai_chat_endpoint(self):
        """Test POST /api/chat endpoint."""
        payload = {
            "messages": [
                {"role": "user", "content": "How can I improve my C++ Linux bullets?"}
            ],
            "resume_context": "Skills: C++, Linux, Low-level programming",
            "jd_context": "Requirements: Strong Linux kernel and C++ expertise",
            "cover_letter_context": "I am eager to contribute to low-level engineering systems."
        }
        response = self.client.post("/api/chat", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("reply", data)
        self.assertGreater(len(data["reply"]), 10)

    def test_rewrite_snippet_endpoint(self):
        """Test POST /api/rewrite-snippet endpoint."""
        payload = {
            "text": "I worked on databases and fixed issues.",
            "instruction": "Make it more impactful and quantifiable for a Senior Backend Engineer role",
            "jd_context": "Lead Backend Platform Engineer with PostgreSQL, high concurrency.",
            "resume_context": "Software Engineer with 4 years experience in SQL, distributed systems."
        }
        response = self.client.post("/api/rewrite-snippet", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertIn("rewritten_text", data)
        self.assertGreater(len(data["rewritten_text"]), 10)

    def test_export_template_5_lorna_docx(self):
        """Test POST /api/export-custom-docx with Template 5 (Lorna Alvarado style)."""
        payload = {
            "contact_info": {
                "full_name": "Lorna Alvarado",
                "professional_title": "Digital Marketing Specialist",
                "phone": "+123-456-7890",
                "email": "hello@reallygreatsite.com",
                "location": "123 Anywhere St., Any City"
            },
            "tailored_cv": {
                "professional_summary": "Experienced Digital Marketing Specialist with a focus on branding and SEO.",
                "skills_section": ["Web Design", "Branding", "Graphic Design", "SEO", "Marketing", "Copywriting & Story writing"],
                "work_experience": [
                    {
                        "company": "Larana Inc, Branding",
                        "job_title": "Social Media Manager",
                        "start_date": "2019",
                        "end_date": "2022",
                        "bullet_points": [{"optimized_text": "Led social media campaigns increasing brand engagement by 45%."}]
                    }
                ],
                "education": [
                    {
                        "institution": "Fauget University",
                        "degree": "Master Of Marketing and Business",
                        "graduation_date": "2011 - 2014"
                    }
                ],
                "key_achievements": [
                    {"title": "The Best Employee of the Year", "description": "Oct 2019 | Liceria & Co."}
                ],
                "languages": [{"language": "English", "proficiency": "Native"}, {"language": "French", "proficiency": "Fluent"}]
            },
            "template_style": "template_5_lorna",
            "columns": 2,
            "font_name": "Outfit",
            "doc_title": "Lorna_Alvarado_Marketing_Resume"
        }
        response = self.client.post("/api/export-custom-docx", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertIn("Lorna_Alvarado_Marketing_Resume.docx", data["filename"])
        dl_res = self.client.get(data["download_url"])
        self.assertEqual(dl_res.status_code, 200)
        self.assertGreater(len(dl_res.content), 1000)

    def test_export_cover_letter_templates(self):
        """Test POST /api/export-cover-letter-docx with Minimalist and Navy templates."""
        for tpl_style in ["cl_template_1_centered", "cl_template_2_minimalist", "cl_template_3_navy"]:
            payload = {
                "contact_info": {
                    "full_name": "Lorna Alvarado",
                    "email": "hello@reallygreatsite.com",
                    "phone": "+123-456-7890",
                    "location": "123 Anywhere St., Any City"
                },
                "paragraphs": [
                    "I am writing to express my enthusiasm for the Digital Marketing Lead position.",
                    "With extensive experience in SEO, copywriting, and visual branding, I have scaled multi-channel campaigns.",
                    "Furthermore, my track record in leading cross-functional creative teams has driven high ROI.",
                    "I look forward to discussing how my capabilities align with your strategic growth goals."
                ],
                "salutation": "Dear Hiring Manager,",
                "sign_off": "Best regards,",
                "font_name": "Outfit",
                "template_style": tpl_style,
                "doc_title": f"Lorna_Cover_Letter_{tpl_style}"
            }
            response = self.client.post("/api/export-cover-letter-docx", json=payload)
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertTrue(data["success"])
            dl_res = self.client.get(data["download_url"])
            self.assertEqual(dl_res.status_code, 200)
            self.assertGreater(len(dl_res.content), 1000)

    def test_cover_letter_template_registry_includes_statement_style(self):
        """Ensure the new cover-letter template is included in the UI registry and export pipeline."""
        with open("templates/index.html", "r", encoding="utf-8") as fh:
            html = fh.read()
        with open("static/app.js", "r", encoding="utf-8") as fh:
            js = fh.read()

        self.assertIn("cl_template_7_statement", html)
        self.assertIn("cl_template_7_statement", js)
        self.assertIn("Statement Accent", html)


    def test_export_template_6_aisha(self):
        """Test POST /api/export-custom-docx endpoint with Template 6 Aisha Rahman Slate Teal Sidebar."""
        payload = {
            "contact_info": {
                "full_name": "Aisha Rahman",
                "professional_title": "AI Engineer",
                "email": "hello@greatsite.com",
                "phone": "+123-456-7890",
                "location": "123 Anywhere St., Any City",
                "portfolio_url": "www.greatsite.com"
            },
            "tailored_cv": {
                "professional_summary": "Innovative AI Engineer with deep expertise in deep learning, NLP, and production ML pipelines.",
                "skills_section": ["Artificial Intelligence", "Machine Learning", "Python", "PyTorch", "TensorFlow", "Kubernetes"],
                "work_experience": [
                    {
                        "company": "Mode AI",
                        "job_title": "AI Engineer",
                        "start_date": "January 2022",
                        "end_date": "Present",
                        "bullet_points": [
                            {"optimized_text": "Architected end-to-end ML training pipelines reducing latency by 35%."},
                            {"optimized_text": "Deployed LLM fine-tuning serving infrastructure handling millions of daily requests."}
                        ]
                    }
                ],
                "education": [
                    {
                        "institution": "University of Tech Excellence",
                        "degree": "B.Sc. in Computer Science",
                        "graduation_date": "2017 - 2021"
                    }
                ],
                "awards_and_scholarships": [
                    "AI Breakthrough Innovation Award 2023",
                    "Deep Learning Research Fellowship"
                ],
                "languages": [
                    {"language": "English", "proficiency": "Native"},
                    {"language": "Spanish", "proficiency": "Professional"}
                ]
            },
            "template_style": "template_6_aisha",
            "columns": 2,
            "font_name": "Outfit",
            "doc_title": "Aisha_Rahman_AI_Engineer_Resume"
        }
        response = self.client.post("/api/export-custom-docx", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertIn("Aisha_Rahman_AI_Engineer_Resume.docx", data["filename"])
        dl_res = self.client.get(data["download_url"])
        self.assertEqual(dl_res.status_code, 200)
        self.assertGreater(len(dl_res.content), 1000)


if __name__ == "__main__":
    unittest.main()

