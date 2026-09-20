"""
Comprehensive 29-Section Mock CV & IT Support Specialist Job Description Fixture.

Stress test dataset exercising all 29 standard, optional, and specialized section types
required by the CV Studio Product Blueprint:
1. Contact Information
2. Professional Profile
3. Career Objective
4. Areas of Expertise
5. Professional Experience
6. Education
7. Technical Skills
8. Soft Skills
9. Certifications
10. Professional Projects
11. Research Experience
12. Research Interests
13. Publications
14. Conferences & Presentations
15. Teaching Experience
16. Training & Courses
17. Awards & Achievements
18. Professional Memberships
19. Leadership Experience
20. Volunteer Experience
21. Extracurricular Activities
22. Speaking Engagements
23. Portfolio
24. Languages
25. Licenses
26. Work Authorization
27. Availability
28. Hobbies & Interests
29. References
"""

from typing import Dict, Any

SAMPLE_IT_SUPPORT_JD = """
Job Title: IT Support Specialist (Tier 2/3)
Company: Alpine Systems Solutions GmbH
Location: Vienna, Austria (Hybrid)

About the Role:
We are looking for an IT Support Specialist to ensure seamless operations across our enterprise IT infrastructure. You will diagnose and resolve complex workstation, network, server, and cloud issues, provide hands-on and remote support for 300+ end users, and automate repetitive administrative workflows.

Key Responsibilities:
- Provide Tier 2 and Tier 3 desktop and network support for Windows, macOS, and Linux environments.
- Manage user accounts, access controls, and group policies in Microsoft 365, Azure Active Directory, and Intune.
- Monitor local network switches, VPN connectivity, firewalls, and Wi-Fi access points.
- Troubleshoot hardware, peripheral, printing, and conferencing equipment.
- Automate routine IT onboarding, software packaging, and maintenance tasks using PowerShell or Python scripting.
- Maintain accurate IT documentation, hardware asset inventory, and ITIL-compliant ticket resolution.

Required Qualifications:
- 3+ years of professional IT support, helpdesk, or systems administration experience.
- Strong knowledge of Windows 10/11, macOS, Active Directory, Azure AD, and Microsoft 365 administration.
- Proven troubleshooting skills in TCP/IP networking, DNS, DHCP, VPNs, and VLANs.
- Scripting ability in PowerShell or Python for workflow automation.
- Excellent customer service and communication skills in English and German.

Preferred Qualifications:
- CompTIA A+, Network+, or Microsoft Certified: Modern Desktop Administrator.
- Experience with IT service desk tools (Jira Service Management, ServiceNow).
- ITIL v4 Foundation certification.
"""


def get_29_section_stress_cv_payload() -> Dict[str, Any]:
    """Returns the complete 29-section structured stress-test candidate payload."""
    contact_info = {
        "full_name": "Dr. Elena Vance",
        "professional_title": "Lead AI Systems Architect & Distributed Computing Engineer",
        "email": "elena.vance@example.com",
        "phone": "+43 660 123 4567",
        "location": "Vienna, Austria",
        "linkedin_url": "linkedin.com/in/elenavance",
        "portfolio_url": "elenavance.dev"
    }

    raw_markdown_resume = """# Dr. Elena Vance
Lead AI Systems Architect & Distributed Computing Engineer
Vienna, Austria | +43 660 123 4567 | elena.vance@example.com | linkedin.com/in/elenavance | elenavance.dev

## Professional Profile
Accomplished Systems Architect and AI Researcher with over 10 years of experience designing fault-tolerant distributed systems, high-throughput machine learning pipelines, and cloud-native infrastructure. Proven track record leading multi-disciplinary engineering teams, deploying mission-critical platforms serving over 500,000 users, and publishing peer-reviewed research in top-tier computer science venues.

## Career Objective
Seeking to lead enterprise architecture and distributed systems modernization, bridging deep academic research with scalable, high-availability software engineering in mission-critical environments.

## Areas of Expertise
- Distributed Systems Architecture & Fault Tolerance
- High-Throughput Deep Learning Inference & Quantization
- Cloud-Native Infrastructure & Kubernetes Orchestration
- High-Performance Network Protocols & Zero-Copy Pipelines
- Technical Governance & Research Team Leadership

## Professional Experience

### Lead AI Systems Architect | Alpine AI Systems GmbH | Vienna, Austria
Jan 2022 - Present
- Spearheaded the design and deployment of an enterprise inference platform, reducing latency by 42% for 200,000+ daily active users.
- Architected Kubernetes-based GPU orchestration cluster that optimized hardware utilization by 35% and saved over €180,000 annually.
- Directed an engineering guild of 14 senior engineers across distributed systems, DevOps, and backend microservices.
- Implemented automated observability pipeline utilizing Prometheus and Grafana, driving mean-time-to-resolution (MTTR) down by 55%.
- Authored internal technical standards for zero-trust security and data sovereignty compliance across EU data centers.

### Senior Distributed Systems Engineer | Danube Tech Labs | Vienna, Austria
Mar 2018 - Dec 2021
- Engineered resilient event-driven data ingestion pipeline processing 4.5 billion events daily with 99.995% uptime SLA.
- Modernized legacy monolithic services into decoupled Go and Python microservices, cutting deployment cycle time from 3 weeks to daily.
- Optimized database query throughput on PostgreSQL and Redis clusters, resolving high-contention bottlenecks during peak traffic.
- Mentored 6 junior and mid-level software engineers through structured pair programming and architectural design reviews.

### Research Software Developer | Vienna Scientific Computing Center | Vienna, Austria
Oct 2014 - Feb 2018
- Developed high-performance C++ and MPI parallel computing modules for large-scale physical simulations on Tier-1 supercomputers.
- Reduced inter-node communication overhead by 28% through custom zero-copy memory buffers and InfiniBand RDMA optimizations.
- Collaborated with international academic partners to benchmark petascale scientific workloads.

## Education

### Ph.D. in Computer Science (Distributed Systems) | TU Wien | Vienna, Austria
2014 - 2018
- Dissertation: "Fault-Tolerant Consensus in Asynchronous High-Throughput Distributed Networks"
- Graduated with Highest Distinction (Sub Auspiciis Praesidentis)

### M.Sc. in Computer Science | University of Vienna | Vienna, Austria
2012 - 2014
- Focus: High-Performance Computing and Parallel Architectures
- Graduated First in Class (GPA: 4.0 / 1.0 Austrian Scale)

## Technical Skills
- Programming Languages: Python, C++, Go, Rust, SQL, TypeScript, Bash, PowerShell
- Cloud & Infrastructure: Microsoft Azure, AWS, Kubernetes, Docker, Terraform, Helm
- Frameworks & Engines: PyTorch, TensorRT, CUDA, FastAPI, gRPC, Apache Kafka
- Databases & Storage: PostgreSQL, Redis, ClickHouse, Apache Cassandra, Ceph
- Systems & Networking: Linux (Debian, RHEL), TCP/IP, InfiniBand, RDMA, Active Directory

## Soft Skills
- Executive & Technical Communication
- Strategic Technology Roadmapping
- Cross-Functional Team Leadership
- Mentorship & Talent Development
- Complex Systems Root Cause Analysis

## Certifications
- AWS Certified Solutions Architect - Professional (2023)
- Certified Kubernetes Administrator (CKA) - Cloud Native Computing Foundation (2022)
- ITIL v4 Foundation in IT Service Management (2021)
- Microsoft Certified: Azure Solutions Architect Expert (2020)

## Professional Projects
- NeuroScale: Open-source distributed model partitioning runtime achieving 3x throughput speedups on multi-node GPU clusters (github.com/elenavance/neuroscale).
- CloudMesh: High-resilience service mesh sidecar optimizing TCP connection pooling for distributed microservices.
- DataShield: Zero-knowledge compliance auditing tool adopted by three Austrian public healthcare organizations.

## Research Experience
- Principal Investigator on EU Horizon 2020 collaborative grant (€1.4M funding) investigating energy-efficient edge neural processing.
- Supervised 8 Master's theses and 12 Bachelor's projects in distributed computing and systems programming.
- Directed laboratory testing benchmarks for next-generation non-volatile memory architectures.

## Research Interests
- Edge AI & Low-Precision Model Quantization
- Asynchronous Byzantine Fault Tolerance
- Neuromorphic Event-Driven Computing
- Zero-Trust Distributed Identity Protocols

## Publications
- Vance, E., & Berger, K. (2023). "Decentralized Model Partitioning for Heterogeneous Edge Accelerators." IEEE Transactions on Parallel and Distributed Systems, 34(8), 2110-2124.
- Vance, E. (2021). "Sub-Millisecond Consensus in Wide-Area Microservice Topologies." Proceedings of ACM EuroSys, 45-59.
- Vance, E., et al. (2019). "Benchmarking RDMA Communication Primitives for Distributed Deep Learning." ACM SIGPLAN Notices, 54(3), 102-115.
- Vance, E. (2017). "Dynamic Resilience in Asynchronous Storage Rings." International Conference on Supercomputing (ICS), 88-99.

## Conferences & Presentations
- Keynote Speaker: "Scaling AI Systems Beyond GPU Boundaries", PyData Vienna 2023.
- Invited Panelist: "The Future of European Sovereign Cloud", EuroSys 2022.
- Session Chair: Distributed File Systems Session, IEEE Cluster Conference 2021.

## Teaching Experience
- Adjunct Senior Lecturer: "Advanced Distributed Systems (CS-402)", TU Wien (Winter Semesters 2020 - Present).
- Course Lead: "High-Performance Python for Engineers", Vienna University of Economics and Business (2019 - 2021).
- Teaching Assistant: "Operating Systems Principles", TU Wien (2014 - 2017).

## Training & Courses
- Advanced Deep Learning Systems - Stanford Online (2022)
- High-Performance GPU Programming with CUDA - NVIDIA Deep Learning Institute (2021)
- Executive Leadership & Strategic Decision Making - Cambridge Judge Business School (2020)

## Awards & Achievements
- Austrian National Innovation Award (Staatspreis Innovation) - Federal Ministry for Climate Action (2023)
- Best Paper Award - ACM EuroSys Workshop on Distributed Infrastructures (2021)
- Promotio sub auspiciis Praesidentis rei publicae - Presidential Honor for Outstanding Academic Excellence (2018)
- TU Wien Distinguished Graduate Fellowship (2014)

## Professional Memberships
- Senior Member, Institute of Electrical and Electronics Engineers (IEEE) (2019 - Present)
- Member, Association for Computing Machinery (ACM) (2014 - Present)
- Board Member, Austrian Computer Society (ÖCG) Distributed Systems Special Interest Group (2021 - Present)

## Leadership Experience
- Technical Steering Committee Chair, OpenMesh Open-Source Foundation (2022 - Present)
- Lead Organizer, Vienna High-Performance Computing Meetup (800+ members) (2018 - Present)
- Departmental Ethics and AI Safety Committee Member, Alpine AI Systems (2022 - Present)

## Volunteer Experience
- Volunteer Mentor, Women in Tech Austria (mentoring 4 early-career engineers annually) (2020 - Present)
- Lead Instructor, CoderDojo Vienna (teaching basic algorithms to secondary school students) (2017 - 2021)
- Disaster Relief Technical Volunteer, Austrian Red Cross Digital Services (2016 - 2019)

## Extracurricular Activities
- Alpine Mountaineering & High-Altitude Ski Touring (Active member Austrian Alpine Club OeAV)
- Marathon Running (Vienna City Marathon 2022, 2023 finisher)
- Technical Volunteer for Mountain Rescue Emergency Radio Infrastructure

## Speaking Engagements
- Invited Guest: "Architecting for Petascale AI", The Cloud Engineering Podcast (Episode 84, 2024)
- Guest Lecturer: "Real-Time Machine Learning Systems", Johannes Kepler University Linz (2023)
- Featured Speaker: "Practical Kubernetes at Scale", Vienna DevOps Days (2022)

## Portfolio
- GitHub: github.com/elenavance (12 public repositories, 1,400+ stars)
- Technical Blog: elenavance.dev/blog (30+ deep-dive systems engineering articles)
- Architectural Blueprints Archive: elenavance.dev/architecture

## Languages
- German: Native (C2)
- English: Bilingual / Full Professional Fluency (C2)
- French: Professional Working Proficiency (B2)
- Italian: Elementary Proficiency (A2)

## Licenses
- European Driving Licence: Categories B, BE, A (Full / Clean record)
- Austrian Amateur Radio Station Operator License (Class 1, Call sign OE1EV)

## Work Authorization
- European Union Citizen (Republic of Austria)
- Unrestricted work authorization for Austria, European Union, and EEA countries

## Availability
- Notice Period: 3 months (available for contract advisory / technical consultation immediately)

## Hobbies & Interests
- Alpine Ski Mountaineering and Rock Climbing
- Classical Piano (Completed Grade 8 ABRSM certification)
- Large-Format Analog Photography and Darkroom Printing

## References
Dr. Marcus Weber
Head of Research & Engineering, Alpine AI Systems GmbH
Email: m.weber@alpine-ai-systems.example.com | Phone: +43 1 711 0022

Prof. Dr. Gerhard Holzinger
Chair of Distributed Systems, TU Wien
Email: holzinger@cs.tuwien.example.ac.at | Phone: +43 1 58801 18401
"""

    return {
        "contact_info": contact_info,
        "raw_markdown_resume": raw_markdown_resume,
        "job_description": SAMPLE_IT_SUPPORT_JD,
        "expected_section_count": 29
    }


DR_ELENA_VANCE_STRESS_RESUME = get_29_section_stress_cv_payload()["raw_markdown_resume"]

