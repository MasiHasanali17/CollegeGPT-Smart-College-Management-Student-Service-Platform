"""
router.py

Intelligent analytics router.

Handles:
- Courses
- Faculties
- Hostels
- Fees
- Admission
- Statistics

Returns:

{
    "handled": bool,
    "intent": "...",
    "confidence": float,
    "result": ...
}
"""

from analytics import (
    course,
    faculty,
    hostel,
    fees,
    admission,
    statistics,
)


CONFIDENCE_THRESHOLD = 0.60


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

def normalize(text):

    if not text:
        return ""

    return text.lower().strip()


def score(text, keywords):

    total = 0

    for keyword in keywords:

        if keyword in text:
            total += 1

    return total


# ---------------------------------------------------------
# Entity Extraction
# ---------------------------------------------------------

def extract_course(query):

    q = normalize(query)

    aliases = {
        "btech": "b.tech",
        "b tech": "b.tech",
        "b.tech": "b.tech",
        "mtech": "m.tech",
        "m tech": "m.tech",
        "mba": "mba",
        "bca": "bca",
        "bba": "bba",
    }


    for key, value in aliases.items():

        if key in q:

            for c in course.course_names():

                if value in c.lower():

                    return c


    for c in course.course_names():

        if c.lower() in q:

            return c


    return None



def extract_faculty(query):

    q = normalize(query)


    for f in faculty.faculty_names():

        if f.lower() in q:

            return f


    aliases = {

        "engineering":
            "Faculty of Engineering and Technology",

        "technology":
            "Faculty of Engineering and Technology",

        "medicine":
            "Faculty of Medicine",

        "management":
            "Faculty of Management Studies",

        "pharmacy":
            "Faculty of Pharmacy",

        "law":
            "Faculty of Law",

        "nursing":
            "Faculty of Nursing",

        "agriculture":
            "Faculty of Agriculture"

    }


    for key, value in aliases.items():

        if key in q:

            return value


    return None



def extract_hostel(query):

    q = normalize(query)

    for h in hostel.hostel_names():

        if h.lower() in q:
            return h

    return None


# ---------------------------------------------------------
# Main Router
# ---------------------------------------------------------

def route(query):

    q = normalize(query)

    course_name = extract_course(q)

    faculty_name = extract_faculty(q)

    hostel_name = extract_hostel(q)


    candidates = []


    # =====================================================
    # Statistics
    # =====================================================

    if score(q,[
        "statistics",
        "stats",
        "dashboard",
        "overview",
        "summary"
    ]):

        candidates.append({

            "intent":"statistics",

            "confidence":1.00,

            "result":statistics.dashboard()

        })

        # =====================================================
    # Course Statistics
    # =====================================================
    

    if score(q, [

        "how many course",
        "how many courses",
        "number of course",
        "number of courses",
        "total course",
        "total courses",
        "course count",
        "courses available",
        "course available"

    ]):

        candidates.append({

            "intent": "course_count",

            "confidence": 1.0,

            "result": course.total_courses()

        })
    # =====================================================
    # Course
    # =====================================================

    if course_name:


        if score(q,[

            "fee",
            "fees",
            "cost",
            "price"

        ]):

            candidates.append({

                "intent":"course_fee",

                "confidence":0.98,

                "result":course.tuition_fee(course_name)

            })


        if score(q,[

            "duration",
            "years",
            "length"

        ]):

            candidates.append({

                "intent":"course_duration",

                "confidence":0.98,

                "result":course.duration(course_name)

            })


        if score(q,[

            "specialization",
            "specializations",
            "branch",
            "branches"

        ]):

            candidates.append({

                "intent":"course_specializations",

                "confidence":0.98,

                "result":course.specializations(course_name)

            })


        candidates.append({

            "intent":"course_details",

            "confidence":0.80,

            "result":course.details(course_name)

        })
    # =====================================================
    # Course List
    # =====================================================

    if score(q, [

        "list all course",
        "list all courses",
        "show all course",
        "show all courses",
        "all courses",
        "available courses",
        "courses list"

    ]):

        candidates.append({

            "intent": "course_list",

            "confidence": 1.0,

            "result": course.course_names()

        })

    # =====================================================
    # Faculty Statistics
    # =====================================================

    if score(q, [

        "how many faculty",
        "how many faculties",
        "number of faculty",
        "number of faculties",
        "total faculty",
        "total faculties",
        "faculty count"

    ]):

        candidates.append({

            "intent": "faculty_count",

            "confidence": 1.0,

            "result": faculty.total_faculties()

        })


    # =====================================================
    # Faculty List
    # =====================================================

    if score(q, [

        "list all faculty",
        "list all faculties",
        "show all faculty",
        "show all faculties",
        "all faculties",
        "faculty list"

    ]):

        candidates.append({

            "intent": "faculty_list",

            "confidence": 1.0,

            "result": faculty.faculty_names()

        })
    # =====================================================
    # Faculty
    # =====================================================

    if faculty_name:


        candidates.append({

            "intent":"faculty",

            "confidence":0.95,

            "result":faculty.summary(faculty_name)

        })

    # =====================================================
    # Hostel
    # =====================================================


    # Total hostel count

    if score(q,[

        "how many hostel",
        "how many hostels",
        "number of hostel",
        "number of hostels",
        "total hostel",
        "total hostels",
        "hostel count",
        "hostels count",
        "hostel available",
        "hostels available"

    ]):

        candidates.append({

            "intent":"hostel_count",

            "confidence":1.0,

            "result":hostel.total_hostels()

        })



    # Complete hostel list

    if score(q,[

        "list all hostel",
        "list all hostels",
        "list hostel",
        "list hostels",
        "all hostel",
        "all hostels",
        "show hostel",
        "show hostels",
        "show all hostel",
        "show all hostels"

    ]):

        candidates.append({

            "intent":"hostel_list",

            "confidence":1.0,

            "result":hostel.hostel_names()

        })



    # Specific hostel details

    if hostel_name:

        candidates.append({

            "intent":"hostel_details",

            "confidence":0.95,

            "result":hostel.details(hostel_name)

        })



    # Hostel WiFi

    if score(q,[

        "wifi",
        "internet"

    ]):

    

        candidates.append({

            "intent":"wifi",

            "confidence":0.95,

            "result":hostel.wifi()

        })


    # Hostel Facilities

    if score(q,[

        "hostel facilities",
        "hostel facility",
        "facilities in hostel",
        "hostel amenities",
        "hostel services"

    ]):

        candidates.append({

            "intent":"hostel_facilities",

            "confidence":0.95,

            "result":hostel.facilities()

        })
    # Hostel Laundry

    if score(q,[

        "laundry",
        "washing"

    ]):

        candidates.append({

            "intent":"laundry",

            "confidence":0.95,

            "result":hostel.laundry()

        })



    # Hostel Mess

    if score(q,[

        "mess",
        "food",
        "meal"

    ]):

        candidates.append({

            "intent":"mess",

            "confidence":0.95,

            "result":hostel.mess()

        })



    # Water

    if score(q,[

        "water",
        "drinking water"

    ]):

        candidates.append({

            "intent":"water",

            "confidence":0.90,

            "result":hostel.water_supply()

        })



    # Room allotment

    if score(q,[

        "allotment",
        "room allotment",
        "room allocation"

    ]):

        candidates.append({

            "intent":"allotment",

            "confidence":0.95,

            "result":hostel.allotment()

        })



    # Cheapest hostel

    if score(q,[

        "cheapest hostel",
        "lowest hostel fee",
        "lowest hostel fees"

    ]):

        candidates.append({

            "intent":"lowest_hostel_fee",

            "confidence":1.0,

            "result":fees.cheapest_hostel()

        })



    # Highest hostel

    if score(q,[

        "highest hostel",
        "costliest hostel",
        "highest hostel fee"

    ]):

        candidates.append({

            "intent":"highest_hostel_fee",

            "confidence":1.0,

            "result":fees.costliest_hostel()

        })





    # =====================================================
    # Fees
    # =====================================================


    if score(q,[

        "cheapest course",
        "lowest course fee",
        "lowest course fees",
        "lowest fee course",
        "cheapest course fee"

    ]):

        candidates.append({

            "intent":"lowest_course_fee",

            "confidence":1.0,

            "result":fees.cheapest_course()

        })



    if score(q,[

        "highest course",
        "highest course fee",
        "highest course fees",
        "costliest course"

    ]):

        candidates.append({

            "intent":"highest_course_fee",

            "confidence":1.0,

            "result":fees.costliest_course()

        })



    # =====================================================
    # Admission
    # =====================================================


    if score(q,[

        "application",
        "admission process",
        "how to apply",
        "apply admission"

    ]):

        candidates.append({

            "intent":"application",

            "confidence":0.95,

            "result":admission.application_process()

        })



    if score(q,[

        "document",
        "documents",
        "required documents"

    ]):

        candidates.append({

            "intent":"documents",

            "confidence":0.95,

            "result":admission.documents()

        })



    if score(q,[

        "entrance",
        "exam",
        "accepted exams"

    ]):

        candidates.append({

            "intent":"entrance",

            "confidence":0.95,

            "result":admission.entrance_exams()

        })



    if score(q,[

        "quota"

    ]):

        candidates.append({

            "intent":"quota",

            "confidence":0.95,

            "result":admission.quota_policy()

        })



    if score(q,[

        "international",
        "nri"

    ]):

        candidates.append({

            "intent":"international",

            "confidence":0.95,

            "result":admission.international()

        })



    if score(q,[

        "gap year",
        "gap"

    ]):

        candidates.append({

            "intent":"gap_year",

            "confidence":0.95,

            "result":admission.gap_year()

        })



    if score(q,[

        "lateral entry",
        "lateral"

    ]):

        candidates.append({

            "intent":"lateral_entry",

            "confidence":0.95,

            "result":admission.lateral_entry()

        })


    # =====================================================
    # No Match
    # =====================================================


    if not candidates:

        return {

            "handled":False,

            "intent":None,

            "confidence":0,

            "result":None

        }



    best = max(

        candidates,

        key=lambda x:x["confidence"]

    )


    best["handled"] = (

        best["confidence"] >= CONFIDENCE_THRESHOLD

    )


    return best



# ---------------------------------------------------------
# Testing
# ---------------------------------------------------------

if __name__ == "__main__":


    from pprint import pprint


    tests = [
        "dashboard",

"statistics",

"university overview",

"overall summary",
        "admission process",

"entrance exam",

"quota policy",

"international admission",

"gap year",

"lateral entry",
        "hostel wifi",

"hostel laundry",

"hostel mess",

"hostel facilities",

"room allotment",

"water supply",
        "engineering faculty details",

"medicine faculty details",
        "how many faculties",

"list all faculties",
        "which is cheapest course",

"which is highest course fee",
        "how many courses available",

"total courses",

"list all courses",

        "how many hostels",

        "total hostels",

        "show all hostels",

        "list all hostels",

        "BTech fees",

        "MBA fee",

        "documents required"

    ]


    for t in tests:

        print("\nQUESTION:",t)

        pprint(route(t))