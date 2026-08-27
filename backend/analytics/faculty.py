"""
faculty.py

Faculty Analytics Module
"""

from analytics.indexer import academic


ACADEMIC = academic()


# ---------------------------------------------------------
# Faculty List
# ---------------------------------------------------------

def all_faculties():

    return ACADEMIC.get("faculties", [])


# ---------------------------------------------------------
# Statistics
# ---------------------------------------------------------

def total_faculties():

    return len(all_faculties())


# ---------------------------------------------------------
# Faculty Names
# ---------------------------------------------------------

def faculty_names():

    return sorted(

        faculty["faculty_name"]

        for faculty in all_faculties()

    )


# ---------------------------------------------------------
# Search Faculty
# ---------------------------------------------------------

def find_faculty(name):

    name = name.lower().strip()

    for faculty in all_faculties():

        if faculty["faculty_name"].lower() == name:

            return faculty

    return None


# ---------------------------------------------------------
# Courses in Faculty
# ---------------------------------------------------------

def courses(name):

    faculty = find_faculty(name)

    if not faculty:

        return []

    return faculty.get("courses", [])


# ---------------------------------------------------------
# Course Names
# ---------------------------------------------------------

def course_names(name):

    return [

        c["course_name"]

        for c in courses(name)

    ]


# ---------------------------------------------------------
# Total Courses
# ---------------------------------------------------------

def total_courses(name):

    return len(courses(name))


# ---------------------------------------------------------
# Specializations
# ---------------------------------------------------------

def total_specializations(name):

    count = 0

    for course in courses(name):

        count += len(

            course.get(

                "specializations",

                []

            )

        )

    return count


# ---------------------------------------------------------
# Faculty Summary
# ---------------------------------------------------------

def summary(name):

    faculty = find_faculty(name)

    if not faculty:

        return None

    return {

        "faculty_name":

            faculty["faculty_name"],

        "total_courses":

            total_courses(name),

        "total_specializations":

            total_specializations(name),

        "courses":

            course_names(name)

    }


# ---------------------------------------------------------
# All Faculty Summaries
# ---------------------------------------------------------

def all_summaries():

    result = []

    for faculty in faculty_names():

        result.append(

            summary(faculty)

        )

    return result


# ---------------------------------------------------------
# Debug
# ---------------------------------------------------------

if __name__ == "__main__":

    print(

        "Total Faculties :",

        total_faculties()

    )

    print()

    print(

        faculty_names()

    )

    print()

    print(

        summary(

            "Faculty of Engineering and Technology"

        )

    )