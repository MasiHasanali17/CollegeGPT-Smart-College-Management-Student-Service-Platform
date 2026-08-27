"""
course.py

Course Analytics Module
"""

import re
from analytics.indexer import academic


ACADEMIC = academic()


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

def _normalize(text):

    return str(text).strip().lower()


def _extract_amount(text):
    """
    Returns first numeric fee found.

    Example:
    ₹ 94,800 -> 94800
    State Quota: ₹ 1,39,000 -> 139000
    """

    if not text:
        return None

    m = re.search(r"₹\s*([\d,]+)", str(text))

    if not m:
        return None

    return int(
        m.group(1).replace(",", "")
    )


# ---------------------------------------------------------
# Faculties
# ---------------------------------------------------------

def faculties():

    return ACADEMIC.get("faculties", [])


# ---------------------------------------------------------
# Courses
# ---------------------------------------------------------

def all_courses():

    result = []

    for faculty in faculties():

        faculty_name = faculty["faculty_name"]

        for course in faculty.get("courses", []):

            item = dict(course)

            item["faculty_name"] = faculty_name

            result.append(item)

    return result


# ---------------------------------------------------------
# Statistics
# ---------------------------------------------------------

def total_courses():

    return len(course_names())


# ---------------------------------------------------------
# Names
# ---------------------------------------------------------

def course_names():

    return sorted({

        c["course_name"]

        for c in all_courses()

    })


# ---------------------------------------------------------
# Search
# ---------------------------------------------------------

def find_course(course_name):

    course_name = _normalize(course_name)

    for course in all_courses():

        if _normalize(course["course_name"]) == course_name:

            return course

    return None


# ---------------------------------------------------------
# Details
# ---------------------------------------------------------

def details(course_name):

    return find_course(course_name)


# ---------------------------------------------------------
# Duration
# ---------------------------------------------------------

def duration(course_name):

    c = find_course(course_name)

    if not c:

        return None

    return c.get("duration")


# ---------------------------------------------------------
# Program Type
# ---------------------------------------------------------

def program_type(course_name):

    c = find_course(course_name)

    if not c:

        return None

    return c.get("program_type")


# ---------------------------------------------------------
# Faculty
# ---------------------------------------------------------

def faculty(course_name):

    c = find_course(course_name)

    if not c:

        return None

    return c.get("faculty_name")


# ---------------------------------------------------------
# Specializations
# ---------------------------------------------------------

def specializations(course_name):

    c = find_course(course_name)

    if not c:

        return []

    return c.get("specializations", [])


# ---------------------------------------------------------
# Tuition Fee
# ---------------------------------------------------------

def tuition_fee(course_name):

    c = find_course(course_name)

    if not c:

        return None

    # Course has direct fee

    if "tuition_fee" in c:

        return c["tuition_fee"]

    specs = c.get("specializations", [])

    if not specs:

        return None

    return specs[0].get("tuition_fee")


# ---------------------------------------------------------
# Lowest Fee Course
# ---------------------------------------------------------

def lowest_fee_course():

    best = None

    best_fee = 10**18

    for course in all_courses():

        if "tuition_fee" in course:

            fee = _extract_amount(course["tuition_fee"])

            if fee and fee < best_fee:

                best_fee = fee
                best = course

        for spec in course.get("specializations", []):

            fee = _extract_amount(
                spec.get("tuition_fee")
            )

            if fee and fee < best_fee:

                best_fee = fee
                best = {

                    "course_name": course["course_name"],
                    "faculty_name": course["faculty_name"],
                    "specialization": spec["name"],
                    "fee": spec["tuition_fee"]
                }

    return best


# ---------------------------------------------------------
# Highest Fee Course
# ---------------------------------------------------------

def highest_fee_course():

    best = None

    best_fee = -1

    for course in all_courses():

        if "tuition_fee" in course:

            fee = _extract_amount(course["tuition_fee"])

            if fee and fee > best_fee:

                best_fee = fee
                best = course

        for spec in course.get("specializations", []):

            fee = _extract_amount(
                spec.get("tuition_fee")
            )

            if fee and fee > best_fee:

                best_fee = fee

                best = {

                    "course_name": course["course_name"],
                    "faculty_name": course["faculty_name"],
                    "specialization": spec["name"],
                    "fee": spec["tuition_fee"]
                }

    return best


# ---------------------------------------------------------
# Debug
# ---------------------------------------------------------

if __name__ == "__main__":

    print("Faculties :", len(faculties()))

    print("Courses :", total_courses())

    print()

    print(course_names())

    print()

    print(details("MBA"))

    print()

    print(specializations("MBA"))

    print()

    print(lowest_fee_course())

    print()

    print(highest_fee_course())