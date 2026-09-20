"""
CLI Interface for the Algorithmic CV Optimization Architecture.

Provides command-line arguments to ingest resumes, analyze target job descriptions,
and output ATS-compliant Word documents.
"""

import argparse
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

from pipeline import run_cv_optimization_pipeline


def main():
    parser = argparse.ArgumentParser(
        description="Algorithmic CV Optimization and Automated Generation via Python & OpenAI Structured Outputs."
    )
    parser.add_argument(
        "--resume", "-r",
        type=str,
        default="sample_data/sample_resume.txt",
        help="Path to candidate resume file (.pdf, .docx, .txt)"
    )
    parser.add_argument(
        "--jd", "-j",
        type=str,
        default="sample_data/job_description.txt",
        help="Path to target job description file (.txt, .docx, .pdf)"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default="Tailored_ATS_Resume.docx",
        help="Destination path for generated DOCX resume"
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Run in offline mock mode without calling the OpenAI API"
    )
    parser.add_argument(
        "--parse-model",
        type=str,
        default="gpt-4o-mini",
        help="OpenAI model for schema extraction (default: gpt-4o-mini)"
    )
    parser.add_argument(
        "--optimize-model",
        type=str,
        default="gpt-4o-mini",
        help="OpenAI model for strategic reframing (default: gpt-4o-mini)"
    )

    args = parser.parse_args()

    resume_path = Path(args.resume)
    jd_path = Path(args.jd)

    if not resume_path.exists():
        print(f"Error: Resume input file not found at '{resume_path}'", file=sys.stderr)
        sys.exit(1)

    if not jd_path.exists():
        print(f"Error: Job description input file not found at '{jd_path}'", file=sys.stderr)
        sys.exit(1)

    try:
        run_cv_optimization_pipeline(
            input_cv_path=str(resume_path),
            input_jd_path=str(jd_path),
            output_docx_path=str(args.output),
            use_mock=args.mock,
            parse_model=args.parse_model,
            optimize_model=args.optimize_model
        )
    except Exception as e:
        print(f"Pipeline error: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
