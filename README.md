# Algorithmic Curriculum Vitae (CV) Optimization Architecture & Web Application

An automated Python engine and interactive web application that ingests unstructured resumes, parses and restructures content into validated schemas using **OpenAI Structured Outputs** (`client.chat.completions.parse`), optimizes content for semantic ATS alignment, and programmatically renders a fully ATS-compliant, single-column Word document (`.docx`).

---

## 🏛 Architectural Overview & Pipeline

```
┌─────────────────────────┐
│ 1. Ingestion & Extract  │  pdfplumber / python-docx / plain text
└────────────┬────────────┘
             │ Raw String Text
┌────────────▼────────────┐
│ 2. Schema Normalization │  OpenAI Structured Outputs -> ResumeSchema & JobRequirementsSchema
└────────────┬────────────┘
             │ Canonical Pydantic Objects
┌────────────▼────────────┐
│ 3. Strategic Reframing  │  Reasoning Models -> TailoredResumeSchema (Action + Context + Metric)
└────────────┬────────────┘
             │ Fact Audit & Keyword Coverage Guardrails
┌────────────▼────────────┐
│ 4. Layout Synthesis     │  python-docx -> ATS Single-Column Styled .docx
└─────────────────────────┘
```

---

## ⚡ Key Features

- **Interactive Web Application**:
  - Drag-and-drop resume upload zone (PDF, DOCX, TXT) and job description editor.
  - 1-click sample data preloader for instant testing.
  - Real-time ATS keyword match gauge & scorecard.
  - Fact audit banner with anti-hallucination verification.
  - Interactive bullet comparison displaying *Original Bullet* ➔ *AI Recruiter Reasoning* ➔ *ATS-Optimized Bullet*.
  - 1-click Word document (`.docx`) download.
- **Strict Schema Enforcement**: Guarantees deterministic model outputs using Pydantic `BaseModel` and OpenAI Structured Outputs (`strict: True`).
- **Reasoning-Assisted Bullet Rewriting**: Bullets generated via `OptimizedBullet` containing `reasoning_steps`, `original_text`, and `optimized_text` formatted as *Action Verb + Action Context + Measurable Result/Impact*.
- **ATS Parsing Protection**:
  - Strict single-column vertical linear flow (eliminates table slicing and text-box dropouts).
  - 0.75-inch page margins.
  - Standard font typography (Arial, 10pt body, 11pt section headings, 18pt header).
  - Punctuation & glyph sanitization (replaces curly quotes, em-dashes, and special bullets with ATS-safe ASCII).
- **Fact Verification & Anti-Hallucination Guardrails**: Cross-references employers, degrees, and institutions between source and tailored resumes to ensure complete factual truthfulness.
- **Mathematical Keyword Alignment**: Computes keyword intersection coverage scores against target job specifications:
  $$\mathcal{S}_{match} = \alpha \left(\frac{|K_R \cap K_E|}{|K_R|}\right) + (1 - \alpha)\cos(\mathbf{v}_R, \mathbf{v}_E)$$

---

## 🚀 Quickstart & Installation

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Launch the Web Application
```bash
python run_web.py
```
Open **[http://127.0.0.1:8000](http://127.0.0.1:8000)** in your browser.

---

### 3. Command-Line Interface (CLI)
```bash
# Run with sample files in mock mode (no API key required)
python cli.py --resume sample_data/sample_resume.txt --jd sample_data/job_description.txt --output Tailored_ATS_Resume.docx --mock

# Run live with OpenAI API key
$env:OPENAI_API_KEY="your-openai-api-key"
python cli.py --resume path/to/resume.pdf --jd path/to/jd.txt --output Tailored_Resume.docx
```

---

## 📂 Project Structure

- [`app.py`](file:///C:/Users/silat/.gemini/antigravity/scratch/cv_optimizer/app.py): FastAPI backend with REST endpoints for file upload, optimization, and downloads.
- [`run_web.py`](file:///C:/Users/silat/.gemini/antigravity/scratch/cv_optimizer/run_web.py): Local web server launcher script.
- [`templates/index.html`](file:///C:/Users/silat/.gemini/antigravity/scratch/cv_optimizer/templates/index.html): Interactive dashboard UI template.
- [`static/styles.css`](file:///C:/Users/silat/.gemini/antigravity/scratch/cv_optimizer/static/styles.css) & [`static/app.js`](file:///C:/Users/silat/.gemini/antigravity/scratch/cv_optimizer/static/app.js): Modern, responsive frontend styles and client logic.
- [`schemas.py`](file:///C:/Users/silat/.gemini/antigravity/scratch/cv_optimizer/schemas.py): Canonical Pydantic schemas (`ResumeSchema`, `JobRequirementsSchema`, `TailoredResumeSchema`).
- [`extractor.py`](file:///C:/Users/silat/.gemini/antigravity/scratch/cv_optimizer/extractor.py): Multi-format parser for PDF, DOCX, and TXT.
- [`sanitizer.py`](file:///C:/Users/silat/.gemini/antigravity/scratch/cv_optimizer/sanitizer.py): ATS-safe character and typography normalization.
- [`optimizer.py`](file:///C:/Users/silat/.gemini/antigravity/scratch/cv_optimizer/optimizer.py): OpenAI Structured Outputs extraction, reframing, and backoff retries.
- [`verification.py`](file:///C:/Users/silat/.gemini/antigravity/scratch/cv_optimizer/verification.py): Anti-hallucination verification and keyword coverage scoring.
- [`renderer.py`](file:///C:/Users/silat/.gemini/antigravity/scratch/cv_optimizer/renderer.py): Programmatic single-column Word document builder.
- [`pipeline.py`](file:///C:/Users/silat/.gemini/antigravity/scratch/cv_optimizer/pipeline.py): End-to-end pipeline coordinator.
- [`cli.py`](file:///C:/Users/silat/.gemini/antigravity/scratch/cv_optimizer/cli.py): Command-line interface.
- [`test_cv_optimizer.py`](file:///C:/Users/silat/.gemini/antigravity/scratch/cv_optimizer/test_cv_optimizer.py) & [`test_web_app.py`](file:///C:/Users/silat/.gemini/antigravity/scratch/cv_optimizer/test_web_app.py): Full test suites.
