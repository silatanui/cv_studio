import os
import re
from schemas import ResumeSchema, JobRequirementsSchema, TailoredResumeSchema, WorkExperience, Education, ContactInformation, OptimizedWorkExperience, OptimizedBullet
from extractor import extract_text_from_file

def smart_heuristic_parse_experience(exp_lines, default_location=""):
    work_exps = []
    
    # Date range regex pattern
    date_pat = re.compile(
        r'(\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?|\d{1,2}[/-]\d{2,4}|\d{4})\b(?:\s*[-–—/]\s*|\s+to\s+)(?:(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?|\d{1,2}[/-]\d{2,4}|\d{4})\b|Present|Current|Now))',
        re.IGNORECASE
    )

    current_entry = {
        "header_lines": [],
        "bullets": []
    }
    entries = []

    for line in exp_lines:
        line_str = line.strip()
        if not line_str:
            continue
        
        is_bullet = line_str.startswith(('•', '-', '*', '–', '■', '○', '◆')) or bool(re.match(r'^\d+[\.\)]\s+', line_str))
        
        if is_bullet:
            bullet_clean = re.sub(r'^[•\-\*–■○◆\d\.\)]+\s*', '', line_str).strip()
            if bullet_clean:
                current_entry["bullets"].append(bullet_clean)
        else:
            # Non-bullet line
            # If we already have bullets in the current entry, a non-bullet line signals a NEW experience!
            if current_entry["bullets"]:
                entries.append(current_entry)
                current_entry = {"header_lines": [line_str], "bullets": []}
            else:
                current_entry["header_lines"].append(line_str)

    if current_entry["header_lines"] or current_entry["bullets"]:
        entries.append(current_entry)

    for entry in entries:
        h_lines = entry["header_lines"]
        bullets = entry["bullets"]
        if not h_lines and not bullets:
            continue

        role = ""
        company = ""
        start_date = "2022"
        end_date = "Present"
        loc = default_location

        remaining_headers = []
        for hl in h_lines:
            d_match = date_pat.search(hl)
            if d_match:
                full_d = d_match.group(1).strip()
                # Split start and end dates
                d_parts = re.split(r'\s*[-–—]\s*|\s+to\s+', full_d, flags=re.IGNORECASE)
                if len(d_parts) >= 2:
                    start_date = d_parts[0].strip()
                    end_date = d_parts[1].strip()
                else:
                    start_date = full_d
                    end_date = "Present"

                # Check if there is text before or after the date on the same line
                text_without_date = hl.replace(full_d, "").strip(" -–—|,()")
                if text_without_date:
                    remaining_headers.append(text_without_date)
            else:
                remaining_headers.append(hl)

        # Now parse remaining header lines into role, company, and location
        if len(remaining_headers) == 1:
            single_line = remaining_headers[0]
            parts = [p.strip() for p in re.split(r'[|•]', single_line) if p.strip()]
            if len(parts) >= 2:
                role = parts[0]
                company = parts[1]
                if len(parts) >= 3:
                    loc = parts[2]
            else:
                dash_parts = [p.strip() for p in re.split(r'\s+[-–—]\s+', single_line) if p.strip()]
                if len(dash_parts) >= 2:
                    role = dash_parts[0]
                    company = dash_parts[1]
                else:
                    role = single_line
                    company = "Company"
        elif len(remaining_headers) >= 2:
            role = remaining_headers[0]
            # Second line might be "Company - Location" or "Company | Location"
            sec_line = remaining_headers[1]
            c_parts = [p.strip() for p in re.split(r'[|•]|\s+[-–—]\s+', sec_line) if p.strip()]
            if len(c_parts) >= 2:
                company = c_parts[0]
                loc = c_parts[1]
            else:
                company = sec_line

        if not role and not company:
            role = "Professional Role"
            company = "Organization"
        elif not company:
            company = "Organization"
        elif not role:
            role = "Professional Role"

        work_exps.append(WorkExperience(
            company=company,
            job_title=role,
            start_date=start_date,
            end_date=end_date,
            location=loc,
            bullet_points=bullets or ["Delivered key technical projects and collaborated across functional teams."]
        ))

    return work_exps

cv_txt = extract_text_from_file('sample_data/sample_resume.txt')
jd_txt = extract_text_from_file('sample_data/job_description.txt')

from optimizer import heuristic_parse_resume
# Let's test the experience segmentation on sample_resume.txt
lines = [l.strip() for l in cv_txt.split('\n') if l.strip()]
sections = {}
current_sec = "header"
sections[current_sec] = []
sec_keywords = {
    "summary": ["summary", "professional summary", "profile", "about me", "executive summary"],
    "experience": ["work experience", "experience", "employment history", "professional experience", "work history"],
    "skills": ["skills", "technical skills", "core competencies", "key skills", "technologies"],
    "education": ["education", "academic background", "qualifications", "academic qualifications"],
    "achievements": ["key achievements", "achievements", "accomplishments", "highlights"],
    "academic_work": ["projects", "academic projects", "academic work", "key projects"],
    "awards": ["awards", "scholarships", "honors", "awards & scholarships"],
    "languages": ["languages", "language proficiency"],
    "referees": ["referees", "references"]
}

for line in lines[1:]:
    cleaned = line.strip().lower().rstrip(':')
    matched_sec = None
    for sec_name, triggers in sec_keywords.items():
        if cleaned in triggers or any(cleaned == t for t in triggers):
            matched_sec = sec_name
            break
    if matched_sec:
        current_sec = matched_sec
        if current_sec not in sections:
            sections[current_sec] = []
    else:
        sections[current_sec].append(line)

exps = smart_heuristic_parse_experience(sections.get("experience", []))
print(f"SMART HEURISTIC PARSED {len(exps)} EXPERIENCES:")
for i, exp in enumerate(exps):
    print(f"[{i}] {exp.job_title} at {exp.company} ({exp.start_date} - {exp.end_date}, {exp.location}) Bullets: {len(exp.bullet_points)}")

