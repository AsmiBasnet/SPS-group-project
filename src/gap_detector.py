# ================================================
# Policy Gap Detector
# Scans indexed chunks and flags missing HR topics
# ================================================

# Standard HR topics every policy handbook should cover
REQUIRED_TOPICS = {
    "FMLA / Medical Leave": [
        "fmla", "family leave", "medical leave", "maternity", "paternity",
        "parental leave", "serious health condition"
    ],
    "Harassment & Discrimination": [
        "harassment", "discrimination", "hostile work", "sexual harassment",
        "equal opportunity", "retaliation"
    ],
    "Vacation & Sick Leave": [
        "vacation", "sick leave", "pto", "paid time off",
        "annual leave", "sick day"
    ],
    "ADA Accommodation": [
        "ada", "accommodation", "disability", "reasonable accommodation",
        "americans with disabilities"
    ],
    "Absenteeism & Tardiness": [
        "absenteeism", "tardiness", "attendance", "no call no show",
        "unexcused absence"
    ],
    "Termination Policy": [
        "termination", "dismissal", "separation", "at-will",
        "wrongful termination", "layoff"
    ],
    "Disciplinary Process": [
        "disciplinary", "written warning", "verbal warning",
        "performance improvement", "pip", "corrective action"
    ],
    "Notice Period": [
        "notice period", "two weeks notice", "resignation",
        "voluntary separation"
    ],
    "Code of Conduct": [
        "code of conduct", "workplace behavior", "ethics",
        "conflict of interest", "confidentiality"
    ],
    "Remote Work / Flexible Work": [
        "remote work", "work from home", "telecommute",
        "flexible work", "hybrid"
    ]
}


def detect_gaps(chunks):
    """
    Scan all indexed chunks and return:
    - covered  : list of topics found in the documents
    - gaps     : list of topics NOT found — these are missing policies
    - coverage : percentage of topics covered
    """
    if not chunks:
        return [], list(REQUIRED_TOPICS.keys()), 0

    # Join all chunk text into one lowercase searchable string
    all_text = " ".join(c["text"].lower() for c in chunks)

    covered = []
    gaps = []

    for topic, keywords in REQUIRED_TOPICS.items():
        found = any(kw in all_text for kw in keywords)
        if found:
            covered.append(topic)
        else:
            gaps.append(topic)

    total = len(REQUIRED_TOPICS)
    coverage = round((len(covered) / total) * 100) if total > 0 else 0

    return covered, gaps, coverage
