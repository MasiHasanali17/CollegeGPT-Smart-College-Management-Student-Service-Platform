"""
fees.py

Fee Analytics Module
"""

import re

from analytics import course
from analytics import hostel


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

def _extract_amount(text):

    if not text:
        return None

    text = str(text)

    # Ignore USD fees
    if "USD" in text.upper():
        return None

    matches = re.findall(
        r"₹\s*([\d,]+)",
        text
    )

    if not matches:
        return None

    amounts = []

    for m in matches:

        value = int(
            m.replace(",", "")
        )

        # Ignore unrealistic quota values
        if value >= 10000:

            amounts.append(value)


    if not amounts:
        return None

    return min(amounts)



# ---------------------------------------------------------
# Course Fee
# ---------------------------------------------------------

def course_fee(course_name):

    return course.tuition_fee(course_name)



# ---------------------------------------------------------
# Hostel Fee
# ---------------------------------------------------------

def hostel_fee(hostel_name):

    return hostel.fee(hostel_name)



# ---------------------------------------------------------
# Cheapest Course
# ---------------------------------------------------------

def cheapest_course():

    best = None
    lowest = float("inf")


    for c in course.all_courses():

        fee = course.tuition_fee(
            c["course_name"]
        )


        amount = _extract_amount(fee)


        if amount is None:
            continue


        if amount < lowest:

            lowest = amount

            best = {

                "course_name":
                    c["course_name"],

                "faculty_name":
                    c["faculty_name"],

                "fee":
                    fee,

                "amount":
                    amount

            }


    return best



# ---------------------------------------------------------
# Costliest Course
# ---------------------------------------------------------

def costliest_course():

    best = None
    highest = 0


    for c in course.all_courses():

        fee = course.tuition_fee(
            c["course_name"]
        )


        amount = _extract_amount(fee)


        if amount is None:
            continue


        if amount > highest:

            highest = amount

            best = {

                "course_name":
                    c["course_name"],

                "faculty_name":
                    c["faculty_name"],

                "fee":
                    fee,

                "amount":
                    amount

            }


    return best



# ---------------------------------------------------------
# Cheapest Hostel
# ---------------------------------------------------------

def cheapest_hostel():

    return hostel.lowest_fee()



# ---------------------------------------------------------
# Costliest Hostel
# ---------------------------------------------------------

def costliest_hostel():

    return hostel.highest_fee()



# ---------------------------------------------------------
# Fee Summary
# ---------------------------------------------------------

def summary():

    return {

        "cheapest_course":
            cheapest_course(),

        "costliest_course":
            costliest_course(),

        "cheapest_hostel":
            cheapest_hostel(),

        "costliest_hostel":
            costliest_hostel()

    }



# ---------------------------------------------------------
# Search Course Fees
# ---------------------------------------------------------

def search_courses(max_fee=None):

    result = []


    for c in course.all_courses():

        fee = course.tuition_fee(
            c["course_name"]
        )


        amount = _extract_amount(fee)


        if amount is None:
            continue


        if max_fee is None or amount <= max_fee:

            result.append({

                "course_name":
                    c["course_name"],

                "faculty":
                    c["faculty_name"],

                "fee":
                    fee

            })


    return sorted(

        result,

        key=lambda x:
            _extract_amount(x["fee"])

    )



# ---------------------------------------------------------
# Search Hostel Fees
# ---------------------------------------------------------

def search_hostels(max_fee=None):

    result = []


    for h in hostel.all_hostels():

        amount = _extract_amount(

            h["fees_per_annum"]

        )


        if amount is None:
            continue


        if max_fee is None or amount <= max_fee:

            result.append({

                "hostel":
                    h["name"],

                "occupancy":
                    h["room_occupancy"],

                "ac":
                    h["ac_non_ac"],

                "fee":
                    h["fees_per_annum"]

            })


    return sorted(

        result,

        key=lambda x:
            _extract_amount(x["fee"])

    )



# ---------------------------------------------------------
# Statistics
# ---------------------------------------------------------

def statistics():

    return {

        "course_fee_records":
            len(search_courses()),

        "hostel_fee_records":
            len(search_hostels())

    }



# ---------------------------------------------------------
# Debug
# ---------------------------------------------------------

if __name__ == "__main__":

    print(summary())

    print()

    print(statistics())