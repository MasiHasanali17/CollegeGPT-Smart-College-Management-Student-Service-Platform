"""
statistics.py

Aggregated statistics for Campus Genius Analytics.
"""

from analytics import course
from analytics import faculty
from analytics import hostel
from analytics import fees
from analytics import admission


# ---------------------------------------------------------
# Academic Statistics
# ---------------------------------------------------------

def academic():

    return {
        "total_faculties": faculty.total_faculties(),
        "total_courses": course.total_courses(),
        "faculty_names": faculty.faculty_names()
    }


# ---------------------------------------------------------
# Hostel Statistics
# ---------------------------------------------------------

def hostel_statistics():

    return {
        "total_hostels": hostel.total_hostels(),
        "boys_hostels": len(hostel.boys_hostels()),
        "girls_hostels": len(hostel.girls_hostels()),
        "ac_rooms": len(hostel.ac_rooms()),
        "non_ac_rooms": len(hostel.non_ac_rooms())
    }


# ---------------------------------------------------------
# Fee Statistics
# ---------------------------------------------------------

def fee_statistics():

    return {
        "cheapest_course": fees.cheapest_course(),
        "costliest_course": fees.costliest_course(),
        "cheapest_hostel": fees.cheapest_hostel(),
        "costliest_hostel": fees.costliest_hostel()
    }


# ---------------------------------------------------------
# Admission Statistics
# ---------------------------------------------------------

def admission_statistics():

    return admission.statistics()


# ---------------------------------------------------------
# Overall Dashboard
# ---------------------------------------------------------

def dashboard():

    return {

        "academic": academic(),

        "hostel": hostel_statistics(),

        "fees": fee_statistics(),

        "admission": admission_statistics()

    }


# ---------------------------------------------------------
# Human-readable Summary
# ---------------------------------------------------------

def summary():

    a = academic()
    h = hostel_statistics()

    return {

        "faculties":
            a["total_faculties"],

        "courses":
            a["total_courses"],

        "hostels":
            h["total_hostels"],

        "boys_hostel_options":
            h["boys_hostels"],

        "girls_hostel_options":
            h["girls_hostels"]

    }


# ---------------------------------------------------------
# Debug
# ---------------------------------------------------------

if __name__ == "__main__":

    from pprint import pprint

    pprint(summary())

    print()

    pprint(dashboard())