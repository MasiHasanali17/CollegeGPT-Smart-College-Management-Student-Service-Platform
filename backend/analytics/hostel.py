"""
hostel.py

Hostel Analytics Module
"""

import re
from analytics.indexer import get


HOSTEL = get("hostel")


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

def _data():
    return HOSTEL.get("hostel_and_residential_life", {})


def _rooms():
    return _data().get("room_details", {}).get("campus_residence_information", {})


def _all_records():
    return boys_hostels() + girls_hostels()


def _extract_fee(text):
    if not text:
        return None

    m = re.search(r"₹\s*([\d,]+)", str(text))
    if not m:
        return None

    return int(m.group(1).replace(",", ""))


def _unique_names(records):
    names = []
    seen = set()

    for hostel in records:
        name = str(hostel.get("name", "")).strip()
        if not name:
            continue

        key = name.lower()
        if key in seen:
            continue

        seen.add(key)
        names.append(name)

    return sorted(names)


# ---------------------------------------------------------
# Boys / Girls
# ---------------------------------------------------------

def boys_hostels():
    return _rooms().get("boys", [])


def girls_hostels():
    return _rooms().get("girls", [])


def all_hostels():
    return _all_records()


# ---------------------------------------------------------
# Statistics
# ---------------------------------------------------------

def total_hostels():
    return len(hostel_names())


def boys_hostel_count():
    return len(_unique_names(boys_hostels()))


def girls_hostel_count():
    return len(_unique_names(girls_hostels()))


# ---------------------------------------------------------
# Hostel Names
# ---------------------------------------------------------

def hostel_names():
    return _unique_names(all_hostels())


def boys_hostel_names():
    return _unique_names(boys_hostels())


def girls_hostel_names():
    return _unique_names(girls_hostels())


# ---------------------------------------------------------
# Search
# ---------------------------------------------------------

def find_hostel(name):
    name = name.lower().strip()

    for hostel in all_hostels():
        if str(hostel.get("name", "")).lower().strip() == name:
            return hostel

    return None


# ---------------------------------------------------------
# Details
# ---------------------------------------------------------

def details(name):
    return find_hostel(name)


# ---------------------------------------------------------
# Fee
# ---------------------------------------------------------

def fee(name):
    hostel = find_hostel(name)
    if hostel:
        return hostel.get("fees_per_annum")
    return None


# ---------------------------------------------------------
# AC / Non AC
# ---------------------------------------------------------

def ac_rooms():
    return [
        hostel
        for hostel in all_hostels()
        if str(hostel.get("ac_non_ac", "")).lower() == "ac"
    ]


def non_ac_rooms():
    return [
        hostel
        for hostel in all_hostels()
        if str(hostel.get("ac_non_ac", "")).lower() == "non ac"
    ]


# ---------------------------------------------------------
# Lowest / Highest Fee
# ---------------------------------------------------------

def lowest_fee():
    best = None
    amount = 10**18

    for hostel in all_hostels():
        fee_value = _extract_fee(hostel.get("fees_per_annum"))
        if fee_value is None:
            continue

        if fee_value < amount:
            amount = fee_value
            best = hostel

    return best


def highest_fee():
    best = None
    amount = -1

    for hostel in all_hostels():
        fee_value = _extract_fee(hostel.get("fees_per_annum"))
        if fee_value is None:
            continue

        if fee_value > amount:
            amount = fee_value
            best = hostel

    return best


# ---------------------------------------------------------
# Mess
# ---------------------------------------------------------

def mess():
    return _data().get("mess_details", {})


# ---------------------------------------------------------
# Laundry
# ---------------------------------------------------------

def laundry():
    return _data().get("laundry_service", {})


# ---------------------------------------------------------
# WiFi
# ---------------------------------------------------------

def wifi():
    return _data().get("wifi_rules", {})

def facilities():

    return {
        "facilities": [
            "Mess",
            "Wi-Fi",
            "Laundry service",
            "Common rooms",
            "Recreation areas",
            "Security",
            "Medical facilities",
            "Sports facilities"
        ]
    }
# ---------------------------------------------------------
# Water
# ---------------------------------------------------------

def water_supply():
    return _data().get("water_supply_timing", {})


# ---------------------------------------------------------
# Room Allotment
# ---------------------------------------------------------

def allotment():
    return _data().get("room_allotment_process", {})


# ---------------------------------------------------------
# Summary
# ---------------------------------------------------------

def summary():
    return {
        "total_hostels": total_hostels(),
        "boys_hostels": boys_hostel_names(),
        "girls_hostels": girls_hostel_names(),
        "boys_hostel_count": boys_hostel_count(),
        "girls_hostel_count": girls_hostel_count(),
        "all_hostels": hostel_names(),
        "cheapest_hostel": lowest_fee(),
        "costliest_hostel": highest_fee(),
        "mess": mess(),
        "laundry": laundry(),
        "wifi": wifi(),
        "water_supply": water_supply(),
        "allotment": allotment(),
    }


# ---------------------------------------------------------
# Debug
# ---------------------------------------------------------

if __name__ == "__main__":
    print("Hostels :", total_hostels())
    print()
    print(hostel_names())
    print()
    print(lowest_fee())
    print()
    print(highest_fee())