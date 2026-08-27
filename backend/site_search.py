"""
site_search.py

Site-wide quick-search — helps someone jump straight to the right PAGE,
course, notice, or hostel by name/keyword. This is deliberately NOT a
Q&A engine (that's what the chatbot already does far better via RAG) —
it's a lightweight navigational search, like a sitemap lookup.

Standalone — reads course/hostel names via the same read-only analytics
functions Interface 1 already uses; never touches the chatbot itself.
"""

STATIC_PAGES = [
    {"title": "Courses", "url": "/courses", "keywords": "courses programs degrees b.tech mba bca"},
    {"title": "Placements", "url": "/placements", "keywords": "placements jobs package recruiters companies salary"},
    {"title": "Achievements", "url": "/achievements", "keywords": "achievements awards rankings accreditation"},
    {"title": "Why Parul", "url": "/why", "keywords": "why choose about university"},
    {"title": "FAQ", "url": "/faq", "keywords": "faq frequently asked questions help"},
    {"title": "Compare Courses", "url": "/compare", "keywords": "compare courses vs comparison"},
    {"title": "Contact", "url": "/contact", "keywords": "contact enquiry email phone address"},
    {"title": "Fee Calculator", "url": "/fee-calculator", "keywords": "fee fees calculator cost tuition price"},
    {"title": "Eligibility Checker", "url": "/eligibility-checker", "keywords": "eligibility criteria qualify eligible"},
    {"title": "Scholarship Checker", "url": "/scholarship-checker", "keywords": "scholarship scholarships financial aid waiver"},
    {"title": "Admission Process", "url": "/admission", "keywords": "admission apply application process documents"},
    {"title": "Track Application", "url": "/admission/track", "keywords": "track application status tracking"},
    {"title": "Campus Tour", "url": "/campus-tour", "keywords": "campus tour video walkthrough"},
    {"title": "Campus Life", "url": "/campus-life", "keywords": "campus life student activities"},
    {"title": "Gallery", "url": "/gallery", "keywords": "gallery photos images pictures"},
    {"title": "Hostel Information", "url": "/hostel-info", "keywords": "hostel accommodation room mess"},
    {"title": "Transport", "url": "/transport", "keywords": "transport bus route commute"},
    {"title": "Chatbot / Campus AI", "url": "/chatbot", "keywords": "chatbot ai assistant ask question chat"},
    {"title": "Student Login", "url": "/login", "keywords": "login student portal sign in"},
]


def search(query):
    query = (query or "").strip().lower()

    if not query:
        return {"pages": [], "courses": [], "notices": [], "hostels": [], "query": ""}

    pages = [
        p for p in STATIC_PAGES
        if query in p["title"].lower() or query in p["keywords"]
    ]

    # Local imports to avoid any import-order issues with Flask app startup
    from analytics import course as course_analytics
    from analytics import hostel as hostel_analytics
    import portal

    def normalize(text):
        return text.lower().replace(".", "").replace(" ", "").replace("-", "")

    normalized_query = normalize(query)

    courses = [
        c for c in course_analytics.course_names()
        if query in c.lower() or normalized_query in normalize(c)
    ][:10]

    hostels = [
        h for h in hostel_analytics.hostel_names()
        if query in h.lower()
    ][:10]

    all_notices = portal.list_notices()
    notices = [
        n for n in all_notices
        if query in n["title"].lower() or query in n["description"].lower()
    ][:10]

    return {
        "pages": pages,
        "courses": courses,
        "notices": notices,
        "hostels": hostels,
        "query": query,
    }
