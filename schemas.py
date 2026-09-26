"""
Pydantic Schemas for Algorithmic CV Optimization Architecture.

Defines canonical data contracts for raw resume extraction, job requirement analysis,
and reasoning-assisted tailored resume generation with support for extended sections
(achievements, skills categories, academic work, awards, languages).
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class ContactInformation(BaseModel):
    """Candidate contact details."""
    full_name: str = Field(description="Full legal name of the candidate")
    professional_title: str = Field(default="", description="Target or current professional title(s)")
    email: str = Field(description="Professional email address")
    phone: str = Field(default="", description="Contact phone number")
    location: str = Field(default="", description="City, State/Country")
    linkedin_url: str = Field(default="", description="LinkedIn profile URL")
    portfolio_url: str = Field(default="", description="Personal website or GitHub URL")


class WorkExperience(BaseModel):
    """Historical employment record extracted from source resume."""
    company: str = Field(description="Name of the employer")
    job_title: str = Field(description="Official position/job title held; normalize source fields such as title, role, role_title, or position_title here")
    start_date: str = Field(description="Start date (e.g., 'Jan 2021' or '2021')")
    end_date: str = Field(description="End date or 'Present'")
    location: str = Field(default="", description="Job location")
    bullet_points: List[str] = Field(default_factory=list, description="Key achievements and responsibilities")


class Education(BaseModel):
    """Educational qualification record."""
    institution: str = Field(description="University or educational institution name")
    degree: str = Field(description="Degree acquired or in progress")
    field_of_study: str = Field(default="", description="Major or domain focus")
    graduation_date: str = Field(default="", description="Graduation year or date range")
    grade: str = Field(default="", description="GPA or grade classification (e.g. 'First Class Honors')")
    honors: List[str] = Field(default_factory=list, description="Academic honors or awards")
    additional_details: List[str] = Field(default_factory=list, description="Additional education details such as coursework, thesis, projects, or activities")


class SkillCategory(BaseModel):
    """Categorized skill group (e.g. Low-Level Systems, Tools)."""
    category_name: str = Field(description="Name of skill domain or group")
    skills: List[str] = Field(default_factory=list, description="Skills under this category")


class AchievementItem(BaseModel):
    """Key achievement highlight."""
    title: str = Field(description="Achievement headline")
    description: str = Field(description="Description of what was achieved and quantifiable impact")


class AcademicWork(BaseModel):
    """Thesis, research paper, or major academic project."""
    title: str = Field(description="Project or thesis title")
    description: str = Field(description="Description of research, technologies, and results")


class MetadataEntry(BaseModel):
    """Structured key-value metadata compatible with strict JSON schemas."""
    key: str = Field(description="Metadata key such as DOI, GPA, or credential ID")
    value: str = Field(description="Metadata value")


class LanguageProficiency(BaseModel):
    """Language fluency."""
    language: str = Field(description="Language name (e.g., English, Swahili, Hungarian)")
    proficiency: str = Field(description="Proficiency level (e.g., 'C1 - Proficient', 'Native')")


class CustomSection(BaseModel):
    """User-defined or custom resume section."""
    title: str = Field(description="Custom section heading title (e.g. CERTIFICATIONS, PROJECTS, PUBLICATIONS, VOLUNTEER EXPERIENCE, MEMBERSHIPS, TRAINING, INTERESTS)")
    content: str = Field(default="", description="Body content text or details for this custom section")
    items: List[str] = Field(default_factory=list, description="List of bullet items or entries in this section")


class SectionItem(BaseModel):
    """Canonical entry item within any section."""
    id: str = Field(default="", description="Unique identifier for the item")
    title: str = Field(default="", description="Primary title (e.g. Job Title, Degree, Project Name, Certification, Publication)")
    subtitle: str = Field(default="", description="Secondary subtitle or role specialization")
    organization: str = Field(default="", description="Company, Institution, Publisher, or Issuing Body")
    date_range: str = Field(default="", description="Dates or timeframe (e.g. 'Jan 2021 - Present', '2022')")
    location: str = Field(default="", description="City, Region, Country or Remote")
    description: str = Field(default="", description="Paragraph narrative, overview, or context")
    bullets: List[str] = Field(default_factory=list, description="Accomplishment or responsibility bullet points")
    tags: List[str] = Field(default_factory=list, description="Skills, technologies, keywords, or topics")
    metadata: List[MetadataEntry] = Field(default_factory=list, description="Metadata such as URL, DOI, credential ID, GPA, or grade")


class SectionModel(BaseModel):
    """Dynamic section container conceptually representing any CV section."""
    id: str = Field(description="Unique section instance ID (e.g. 'sec_work_exp_01')")
    type: str = Field(description="Canonical normalized type (e.g. 'work_experience', 'education', 'publications')")
    title: str = Field(description="Display heading title chosen by user or template (e.g. 'Professional Experience')")
    enabled: bool = Field(default=True, description="Whether this section is visible/active")
    order: int = Field(default=0, description="Visual display order index")
    priority: str = Field(default="high", description="Content priority: 'critical' | 'high' | 'medium' | 'low'")
    visibility: str = Field(default="visible", description="Visibility flag: 'visible' | 'hidden'")
    column_preference: str = Field(default="auto", description="Preferred column placement: 'auto' | 'left' | 'right' | 'main' | 'sidebar'")
    entries: List[SectionItem] = Field(default_factory=list, description="Structured items/entries in this section")
    content: str = Field(default="", description="Optional raw text or markdown paragraph content")
    items: List[str] = Field(default_factory=list, description="Optional flat string bullet items")
    canonical_type: str = Field(default="", description="Canonical normalized section type")
    settings: List[MetadataEntry] = Field(default_factory=list, description="Section-specific styling and layout settings")

    def model_post_init(self, __context: Any) -> None:
        if not self.canonical_type:
            self.canonical_type = self.type


class ResumeSchema(BaseModel):
    """Canonical schema for parsed raw resumes."""
    contact: ContactInformation
    summary: str = Field(default="", description="Executive summary or professional overview")
    key_achievements: List[AchievementItem] = Field(default_factory=list, description="Top key achievements")
    work_experience: List[WorkExperience] = Field(default_factory=list, description="List of work experience items")
    education: List[Education] = Field(default_factory=list, description="List of educational qualifications")
    skills: List[str] = Field(default_factory=list, description="List of skills")
    skill_categories: List[SkillCategory] = Field(default_factory=list, description="Categorized skills list")
    academic_work: List[AcademicWork] = Field(default_factory=list, description="Selected academic work or thesis")
    awards_and_scholarships: List[str] = Field(default_factory=list, description="Awards, honors, scholarships")
    languages: List[LanguageProficiency] = Field(default_factory=list, description="Languages spoken")
    certifications: List[str] = Field(default_factory=list, description="Professional certifications and training")
    publications: List[str] = Field(default_factory=list, description="Published papers, articles, or books")
    volunteer_experience: List[str] = Field(default_factory=list, description="Volunteer, community, or leadership activities")
    professional_memberships: List[str] = Field(default_factory=list, description="Professional memberships, boards, or associations")
    referees: str = Field(default="Available upon Request", description="Reference availability or contacts")
    custom_sections: List[CustomSection] = Field(default_factory=list, description="Custom user-defined sections or additional content")
    sections: List[SectionModel] = Field(default_factory=list, description="Dynamic structured sections list")


class JobRequirementsSchema(BaseModel):
    """Structured requirements extracted from a target job description."""
    job_title: str = Field(description="Target position job title")
    company_name: str = Field(default="", description="Hiring company name")
    required_hard_skills: List[str] = Field(default_factory=list, description="Technical and domain skills required")
    required_soft_skills: List[str] = Field(default_factory=list, description="Interpersonal and operational traits")
    core_responsibilities: List[str] = Field(default_factory=list, description="Primary duties and responsibilities")
    priority_keywords: List[str] = Field(
        default_factory=list,
        description="Top 10 mission-critical terms and technical phrases"
    )


class OptimizedBullet(BaseModel):
    """Reasoning-assisted optimized resume accomplishment bullet."""
    reasoning_steps: str = Field(
        default="",
        description="Detailed analysis of how this accomplishment maps to the target job description."
    )
    original_text: str = Field(default="", description="Original bullet text from source resume")
    optimized_text: str = Field(
        description="ATS-aligned bullet formatted as: Strong Action Verb + Action Context + Measurable Result/Impact."
    )


class OptimizedWorkExperience(BaseModel):
    """Tailored work experience item with reasoning-optimized bullet points."""
    company: str = Field(description="Name of the employer")
    job_title: str = Field(description="Actual job title held, not the employer, department, or target job title")
    start_date: str = Field(description="Start date")
    end_date: str = Field(description="End date")
    location: str = Field(default="", description="Job location")
    bullet_points: List[OptimizedBullet] = Field(
        default_factory=list,
        description="Reframed, high-impact accomplishment bullets"
    )


class TailoredResumeSchema(BaseModel):
    """Final optimized structured resume ready for document synthesis."""
    contact: ContactInformation = Field(description="Candidate contact details")
    professional_summary: str = Field(
        default="",
        description="Targeted executive summary incorporating priority keywords."
    )
    key_achievements: List[AchievementItem] = Field(
        default_factory=list,
        description="Reframed key achievements"
    )
    skills_section: List[str] = Field(
        default_factory=list,
        description="Hard and soft skills categorized to mirror the target job description."
    )
    skill_categories: List[SkillCategory] = Field(
        default_factory=list,
        description="Categorized skills with highlighted target competencies"
    )
    work_experience: List[OptimizedWorkExperience] = Field(
        default_factory=list,
        description="Work experience items with optimized bullet points"
    )
    education: List[Education] = Field(
        default_factory=list,
        description="Educational background"
    )
    academic_work: List[AcademicWork] = Field(
        default_factory=list,
        description="Selected academic work or thesis"
    )
    awards_and_scholarships: List[str] = Field(
        default_factory=list,
        description="Awards and scholarships"
    )
    languages: List[LanguageProficiency] = Field(
        default_factory=list,
        description="Language proficiencies"
    )
    certifications: List[str] = Field(
        default_factory=list,
        description="Relevant professional certifications and training"
    )
    publications: List[str] = Field(
        default_factory=list,
        description="Published papers, articles, or books"
    )
    volunteer_experience: List[str] = Field(
        default_factory=list,
        description="Volunteer, community, or leadership activities"
    )
    professional_memberships: List[str] = Field(
        default_factory=list,
        description="Professional memberships, boards, or associations"
    )
    referees: str = Field(
        default="Available upon Request",
        description="Referee section statement"
    )
    custom_sections: List[CustomSection] = Field(
        default_factory=list,
        description="Custom user-defined sections or additional content"
    )
    sections: List[SectionModel] = Field(
        default_factory=list,
        description="Dynamic structured sections list"
    )
    alignment_score_explanation: str = Field(
        default="",
        description="Summary of how candidate experience satisfies target job requirements."
    )


class CoverLetterSchema(BaseModel):
    """Canonical schema for AI-generated tailored cover letter."""
    recipient_title: str = Field(default="Dear Hiring Team,", description="Salutation to hiring team or manager, e.g. 'Dear Hiring Committee,' or 'Dear Hiring Manager,'")
    recipient_name: str = Field(default="Hiring Manager / Selection Committee", description="Specific recipient title, committee, or person extracted from the Job Description")
    company_name: str = Field(default="", description="Exact name of the hiring organization, ministry, institution, or company from the Job Description")
    department_or_address: str = Field(default="", description="Department, division, team, or location of the hiring organization if mentioned in the Job Description")
    job_title: str = Field(default="", description="Exact title of the target position from the Job Description")
    paragraphs: List[str] = Field(
        description="List of 3 to 4 authentic, persuasive paragraphs strictly grounded in the candidate's uploaded resume and aligning with the target job requirements."
    )
    sign_off: str = Field(default="Sincerely,", description="Formal closing sign-off phrase")


# ====================================================================
# COMMERCIAL INTELLIGENCE & TRUST SCHEMAS (Blueprint Phase 1 & 2)
# ====================================================================

class JobModel(BaseModel):
    """Structured job intelligence model extracted from raw vacancy description."""
    role_title: str = Field(default="Software Professional", description="Official job title")
    seniority: str = Field(default="Mid-Level", description="Seniority level (e.g., Entry, Mid-Level, Senior, Lead, Executive)")
    required_skills: List[str] = Field(default_factory=list, description="Must-have hard and technical skills")
    preferred_skills: List[str] = Field(default_factory=list, description="Nice-to-have or preferred technical skills")
    responsibilities: List[str] = Field(default_factory=list, description="Primary duties and deliverables")
    education_requirement: str = Field(default="Degree or equivalent practical experience", description="Expected academic or certification background")
    soft_signals: List[str] = Field(default_factory=list, description="Interpersonal, collaboration, and ownership traits")
    terminology: List[str] = Field(default_factory=list, description="Domain-specific terminology and industry keywords")


class EvidenceMapItem(BaseModel):
    """Links candidate's factual background to a specific job requirement."""
    requirement: str = Field(description="The job requirement or qualification")
    status: str = Field(description="Evidence status: 'Strong Evidence' | 'Partial Evidence' | 'Indirect Evidence' | 'No Evidence Found'")
    evidence_text: str = Field(default="", description="Candidate factual proof extracted from master CV")
    confidence: float = Field(default=0.9, description="Confidence score between 0.0 and 1.0")
    recommendation: str = Field(default="", description="Actionable recommendation for addressing this requirement")


class JobMatchScoreBreakdown(BaseModel):
    """Diagnostic job match scoring engine with weighted component diagnostics."""
    overall_score: int = Field(default=85, description="Weighted composite match score out of 100")
    match_tier: str = Field(default="Strong Match", description="Tier: 'High Alignment' | 'Strong Match' | 'Moderate Match' | 'Developing Match'")
    interpretation: str = Field(default="Strong alignment with room to improve.", description="Diagnostic takeaway for the user")
    requirement_coverage_score: int = Field(default=85, description="Must-have and preferred requirement coverage (30% weight)")
    evidence_strength_score: int = Field(default=82, description="Direct demonstration in experience (25% weight)")
    keyword_alignment_score: int = Field(default=90, description="Terminology and priority keyword density (15% weight)")
    experience_alignment_score: int = Field(default=84, description="Seniority, scope, and responsibility fit (15% weight)")
    structure_readability_score: int = Field(default=95, description="ATS parseability, chronology, layout (10% weight)")
    application_coherence_score: int = Field(default=90, description="CV and Cover Letter story consistency (5% weight)")
    actionable_recommendations: List[str] = Field(default_factory=list, description="Concrete steps to close gaps and raise score")


class FactualIntegrityReport(BaseModel):
    """Source-grounded verification audit report ensuring zero AI fabrication."""
    integrity_score: int = Field(default=100, description="Percentage of claims verified against master CV (target: 100%)")
    claims_checked: int = Field(default=25, description="Total number of accomplishments and skills audited")
    supported_claims: int = Field(default=25, description="Number of claims directly verified from source evidence")
    unsupported_metrics_count: int = Field(default=0, description="Number of ungrounded numbers or claims detected")
    unsupported_warnings: List[str] = Field(default_factory=list, description="Specific warnings if unverified claims exist")
    status_label: str = Field(default="100% Source-Grounded", description="Status pill text")


class RecruiterReview(BaseModel):
    """Simulated Senior Recruiter & Hiring Manager first-impression audit."""
    first_impression_score: float = Field(default=8.4, description="Recruiter first impression rating out of 10")
    what_stands_out: List[str] = Field(default_factory=list, description="Strongest assets that catch the recruiter's eye within 6 seconds")
    what_gets_overlooked: List[str] = Field(default_factory=list, description="Relevant achievements buried too low or phrased weakly")
    potential_concerns: List[str] = Field(default_factory=list, description="Potential friction points or perceived gaps in requirements")
    recommended_actions: List[str] = Field(default_factory=list, description="Priority changes to maximize interview callback rate")


class InterviewPrep(BaseModel):
    """Role-specific interview preparation talking points and likely questions."""
    key_talking_points: List[str] = Field(default_factory=list, description="Top 3-4 elevator-pitch accomplishments aligned to this role")
    likely_technical_questions: List[str] = Field(default_factory=list, description="Targeted technical/domain questions for this vacancy")
    behavioral_star_prompts: List[str] = Field(default_factory=list, description="STAR-method story prompts mapped to the job requirements")


class ApplicationPackageSnapshot(BaseModel):
    """Snapshot of a completed application package stored in application memory."""
    application_id: str = Field(description="Unique application ID")
    job_title: str = Field(description="Target job title")
    company_name: str = Field(description="Target employer name")
    match_score: int = Field(default=85, description="Overall match score at time of generation")
    created_at: str = Field(description="Creation ISO timestamp")
    status: str = Field(default="Ready", description="Status: 'Draft' | 'Ready' | 'Applied' | 'Interview' | 'Offer' | 'Closed'")
    notes: str = Field(default="", description="User notes or interview dates")


# ====================================================================
# DYNAMIC SECTION ENGINE & 10-DIMENSIONAL AUDIT SCHEMAS
# ====================================================================

class CvQualityDimensionScore(BaseModel):
    """Diagnostic score for a single evaluation dimension."""
    dimension_key: str = Field(description="Internal key: completeness, relevance, structure, readability, achievements, skills, contact, ats_readability, keyword_alignment, formatting")
    name: str = Field(description="Display dimension title")
    score: int = Field(description="Score out of 100")
    max_score: int = Field(default=100, description="Maximum possible score for this dimension")
    weight: float = Field(description="Weight percentage in composite score (0.0 to 1.0)")
    status: str = Field(default="Excellent", description="'Excellent' | 'Good' | 'Needs Improvement' | 'Critical Gap'")
    feedback: str = Field(default="", description="Specific diagnostic feedback")
    actionable_tip: str = Field(default="", description="Concrete step to raise score")


class CvQualityScoreBreakdown(BaseModel):
    """10-dimensional evaluation of CV content quality and technical presentation."""
    overall_score: int = Field(default=90, description="Overall weighted composite quality score out of 100")
    tier: str = Field(default="Executive Grade", description="'Executive Grade' | 'Professional Grade' | 'Needs Polish' | 'Incomplete'")
    summary: str = Field(default="Strong CV structure with high readability and impact.", description="Diagnostic summary")
    dimensions: List[CvQualityDimensionScore] = Field(default_factory=list, description="Scores across 10 evaluation dimensions")
    strengths: List[str] = Field(default_factory=list, description="Top identified assets")
    improvement_recommendations: List[str] = Field(default_factory=list, description="Top actionable recommendations")


class DroppedInformationItem(BaseModel):
    """Record of an item from source CV that was dropped or omitted in rendered output."""
    section_type: str = Field(description="Section type where loss was detected")
    item_title: str = Field(description="Title or description of the missing item")
    severity: str = Field(default="warning", description="'critical' | 'warning' | 'info'")
    message: str = Field(description="Description of what was omitted")


class InformationLossReport(BaseModel):
    """Audit comparing source CV content vs synthesized/rendered document to guarantee zero data loss."""
    is_lossless: bool = Field(default=True, description="True if 100% of meaningful source information is preserved")
    source_section_count: int = Field(default=0, description="Total sections present in source CV")
    rendered_section_count: int = Field(default=0, description="Total sections rendered in document")
    source_item_count: int = Field(default=0, description="Total items/bullets/entries in source CV")
    rendered_item_count: int = Field(default=0, description="Total items/bullets/entries in rendered document")
    preservation_percentage: float = Field(default=100.0, description="Percentage of information preserved (target: 100%)")
    loss_percentage: float = Field(default=0.0, description="Percentage of information lost")
    dropped_items_count: int = Field(default=0, description="Count of dropped items")
    dropped_items: List[DroppedInformationItem] = Field(default_factory=list, description="List of any omitted items")
    summary: str = Field(default="100% of candidate credentials preserved across all templates.", description="Summary audit message")
    status_label: str = Field(default="100% Content Preserved", description="User-facing status badge")


class RecommendedSectionItem(BaseModel):
    """Recommendation for a specific section based on role and candidate background."""
    type: str = Field(description="Canonical section type")
    section_type: str = Field(default="", description="Alias for canonical type")
    title: str = Field(description="Suggested display title")
    rationale: str = Field(description="Why this section is recommended for this role/candidate")
    priority: str = Field(default="high", description="'critical' | 'high' | 'medium' | 'low'")
    is_present_in_cv: bool = Field(default=False, description="Whether the user CV already contains this section")

    def model_post_init(self, __context: Any) -> None:
        if not self.section_type:
            self.section_type = self.type


class SectionRecommendationResult(BaseModel):
    """AI section recommendations tailored to career level, industry, and target role."""
    candidate_profile: str = Field(default="Professional", description="Detected persona (e.g. Software Engineer, Academic, Recent Grad)")
    detected_profile: str = Field(default="", description="Alias for candidate profile")
    career_level: str = Field(default="Mid-Senior", description="Seniority level")
    recommended_core: List[RecommendedSectionItem] = Field(default_factory=list, description="Standard recommended sections")
    recommended_optional: List[RecommendedSectionItem] = Field(default_factory=list, description="Value-add optional sections")
    recommended_specialized: List[RecommendedSectionItem] = Field(default_factory=list, description="Domain-specific specialized sections")
    recommended_sections: List[RecommendedSectionItem] = Field(default_factory=list, description="Combined recommended sections")
    recommended_removals_or_deprioritizations: List[str] = Field(default_factory=list, description="Sections suggested for deprioritization to conserve space")

    def model_post_init(self, __context: Any) -> None:
        if not self.detected_profile:
            self.detected_profile = self.candidate_profile
        if not self.recommended_sections:
            self.recommended_sections = self.recommended_core + self.recommended_optional + self.recommended_specialized
