"""
Document Ingestion and Text Extraction Module.

Extracts raw plain text from PDF, DOCX, and TXT files while preserving
natural paragraph flow and preventing multi-column reading order corruption.
"""

import os
from pathlib import Path
from typing import Union


def extract_text_from_file(file_path: Union[str, Path]) -> str:
    """
    Extracts raw text from PDF, DOCX, or plain text files while preserving
    standard paragraph flow and linear reading order.
    
    Args:
        file_path: Absolute or relative path to the input document.
        
    Returns:
        Extracted plain text string.
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"Source file not found at '{file_path}'")

    suffix = file_path.suffix.lower()
    extracted_text = ""

    if suffix == ".pdf":
        try:
            import pdfplumber
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    # layout=False preserves sequential text flow rather than spatial gaps
                    text = page.extract_text(layout=False)
                    if text:
                        extracted_text += text + "\n"
        except ImportError:
            # Fallback to basic pypdf or raw read if pdfplumber is not installed
            try:
                import pypdf
                reader = pypdf.PdfReader(str(file_path))
                for page in reader.pages:
                    text = page.extract_text()
                    if text:
                        extracted_text += text + "\n"
            except ImportError:
                raise ImportError("Neither 'pdfplumber' nor 'pypdf' is installed. Please install pdfplumber.")

    elif suffix in (".docx", ".doc"):
        try:
            import docx
            doc = docx.Document(file_path)
            for para in doc.paragraphs:
                if para.text.strip():
                    extracted_text += para.text.strip() + "\n"
            # Also extract text from tables if present
            for table in doc.tables:
                for row in table.rows:
                    row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
                    if row_text:
                        extracted_text += row_text + "\n"
        except ImportError:
            raise ImportError("'python-docx' is required to parse DOCX files. Please install python-docx.")

    else:
        # Default plain text handler (TXT, MD, etc.) with encoding fallbacks
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                extracted_text = f.read()
        except UnicodeDecodeError:
            with open(file_path, "r", encoding="latin-1") as f:
                extracted_text = f.read()

    return extracted_text.strip()
