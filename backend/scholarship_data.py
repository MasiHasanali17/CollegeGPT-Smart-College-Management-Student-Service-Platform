"""
scholarship_data.py

Scholarship information for the Scholarship Checker (Interface 1).

IMPORTANT: This data is transcribed from the same knowledge_base.json the
chatbot already uses (categories "scholarships - *"), so the checker never
contradicts what Campus AI would tell a student. Nothing here is invented.
Ranges/figures are kept exactly as hedged in the source ("commonly",
"e.g.") rather than presented as precise guarantees.

This file is standalone — it does not touch backend/analytics/ (the
chatbot's data layer) at all.
"""

SCHOLARSHIPS = {
    "merit": {
        "title": "Merit-Based Scholarship",
        "description": (
            "Awarded to students with outstanding academic performance in their qualifying "
            "examination (Class 12 for UG, graduation for PG) or in university semester results."
        ),
        "criteria": (
            "Commonly tiered by percentage/CGPA brackets (e.g. 95%+, 90-94.9%, 85-89.9%), with "
            "higher brackets receiving a greater percentage waiver on tuition fee."
        ),
        "renewal": (
            "Typically renewable each year subject to maintaining a minimum required "
            "CGPA/percentage and satisfactory attendance."
        ),
    },
    "sports": {
        "title": "Sports Quota Scholarship",
        "description": (
            "Available for students with notable district/state/national/international-level "
            "sporting achievements, verified through certificates and/or a sports trial."
        ),
        "criteria": (
            "Partial to full tuition fee waiver depending on the level of achievement, along "
            "with sports quota seat consideration."
        ),
        "renewal": None,
    },
    "defense": {
        "title": "Defense Wards Scholarship",
        "description": (
            "Fee concession for wards (children) of serving or retired Defence/Paramilitary "
            "personnel, and in some cases for war widows/dependents, subject to submission of "
            "valid service/relationship proof."
        ),
        "criteria": (
            "Typically a percentage-based tuition fee waiver, varying by category (serving/retired/"
            "martyred personnel dependents often receive the highest waiver tier)."
        ),
        "renewal": None,
    },
    "ews": {
        "title": "Economically Weaker Section (EWS) Scholarship",
        "description": (
            "Fee concession for students from economically weaker sections, based on verified "
            "family income criteria (commonly an annual family income threshold, e.g. below "
            "₹2.5-8 lakh depending on the scheme)."
        ),
        "criteria": (
            "Partial tuition fee waiver, subject to submission of a valid income certificate "
            "issued by a competent government authority."
        ),
        "renewal": None,
    },
    "minority": {
        "title": "Minority Scholarship",
        "description": (
            "Fee assistance for students belonging to recognized minority communities, often in "
            "coordination with central/state government minority scholarship schemes (e.g. "
            "Post-Matric Scholarship for Minorities)."
        ),
        "criteria": (
            "Varies based on the specific government scheme; the university typically facilitates "
            "application and documentation support rather than funding this scholarship directly."
        ),
        "renewal": None,
    },
    "state_govt": {
        "title": "State Government Scholarship",
        "description": (
            "Students may be eligible for Gujarat state government scholarship schemes (e.g. for "
            "SC/ST/OBC/EWS categories, or state merit scholarships), applied for through the "
            "state's scholarship portal with university-issued bonafide/fee certificates."
        ),
        "criteria": (
            "The university's accounts/scholarship cell assists with issuing required certificates "
            "and verifying enrollment status for these government-administered schemes."
        ),
        "renewal": None,
    },
}

GENERAL_NOTE = (
    "Scholarships are generally not combinable beyond a specified maximum aggregate waiver "
    "percentage; confirm the current-year scholarship policy and application window with the "
    "accounts/scholarship cell."
)


def check_eligibility(percentage, category, sports_achiever, defense_ward, income_lakh):
    """
    Returns a list of scholarship dicts (from SCHOLARSHIPS) that the student
    should look into, based on what they entered. This is a general-fit
    check, not a final determination — the source data itself hedges with
    "commonly"/"e.g.", so we surface that instead of pretending precision.
    """

    matches = []

    if percentage is not None:
        if percentage >= 85:
            tier = "95%+ tier" if percentage >= 95 else ("90-94.9% tier" if percentage >= 90 else "85-89.9% tier")
            matches.append({**SCHOLARSHIPS["merit"], "your_tier": tier})

    if sports_achiever:
        matches.append(SCHOLARSHIPS["sports"])

    if defense_ward:
        matches.append(SCHOLARSHIPS["defense"])

    if income_lakh is not None and income_lakh <= 8:
        matches.append(SCHOLARSHIPS["ews"])

    if category == "minority":
        matches.append(SCHOLARSHIPS["minority"])

    if category in ("sc", "st", "obc", "ews"):
        matches.append(SCHOLARSHIPS["state_govt"])

    return matches
