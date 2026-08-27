"""
indexer.py

Creates structured indexes from all datasets.

Every analytics module imports data from here
instead of reading JSON files again.
"""

from analytics.loader import load_all

# ---------------------------------------------------------
# Global Index
# ---------------------------------------------------------

INDEX = {}

_BUILT = False


# ---------------------------------------------------------
# Build Index
# ---------------------------------------------------------

def build(force=False):

    global INDEX
    global _BUILT

    if _BUILT and not force:
        return INDEX

    datasets = load_all(force_reload=force)

    INDEX = {

        # Raw datasets
        "datasets": datasets,

        # Main structured datasets
        "academic": datasets.get(
            "academic_details_parul",
            {}
        ),

        "admission": datasets.get(
            "admissions_parul_details",
            {}
        ),

        "hostel": datasets.get(
            "hostel_residential_life_parul_details",
            {}
        ),

        "faculty": datasets.get(
            "faculty_teaching_staff_parul_details",
            {}
        ),

        "placement": datasets.get(
            "placements_parul_details",
            {}
        ),

        "fees": datasets.get(
            "fees_financial_aid_parul_details",
            {}
        ),

        "transport": datasets.get(
            "transport_commute_parul_details",
            {}
        ),

        "calendar": datasets.get(
            "academic_calendar_parul_details",
            {}
        )
    }

    _BUILT = True

    return INDEX


# ---------------------------------------------------------
# Get Complete Index
# ---------------------------------------------------------

def get_index():

    if not _BUILT:
        build()

    return INDEX


# ---------------------------------------------------------
# Get Single Dataset
# ---------------------------------------------------------

def get(name):

    if not _BUILT:
        build()

    return INDEX.get(name)


# ---------------------------------------------------------
# Academic Shortcut
# ---------------------------------------------------------

def academic():

    return get("academic")


# ---------------------------------------------------------
# Faculties Shortcut
# ---------------------------------------------------------

def faculties():

    data = academic()

    return data.get("faculties", [])


# ---------------------------------------------------------
# Courses Shortcut
# ---------------------------------------------------------

def courses():

    result = []

    for faculty in faculties():

        result.extend(
            faculty.get("courses", [])
        )

    return result


# ---------------------------------------------------------
# Statistics
# ---------------------------------------------------------

def stats():

    return {

        "datasets": len(
            INDEX["datasets"]
        ),

        "faculties": len(
            faculties()
        ),

        "courses": len(
            courses()
        )
    }


# ---------------------------------------------------------
# Debug
# ---------------------------------------------------------

if __name__ == "__main__":

    build()

    print("=" * 60)

    print(stats())

    print("=" * 60)