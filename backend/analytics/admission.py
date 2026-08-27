"""
admission.py

Admission Analytics Module
"""

from analytics.indexer import get


ADMISSION = get("admission")


# ---------------------------------------------------------
# Helper
# ---------------------------------------------------------

def _data():

    return ADMISSION.get("admissions", {})


# ---------------------------------------------------------
# Application Process
# ---------------------------------------------------------

def application_process():

    return _data().get("application_process", {})


def application_steps():

    return application_process().get("steps", [])


# ---------------------------------------------------------
# Important Dates
# ---------------------------------------------------------

def important_dates():

    return _data().get("important_dates_pattern", {})


# ---------------------------------------------------------
# Entrance Exams
# ---------------------------------------------------------

def entrance_exams():

    return _data().get("entrance_exams_accepted", {})


def national_exams():

    return entrance_exams().get(
        "national_level_exams",
        []
    )


def university_exam():

    return entrance_exams().get(
        "university_conducted"
    )


# ---------------------------------------------------------
# Documents
# ---------------------------------------------------------

def documents():

    return _data().get(
        "document_checklist",
        {}
    )


def ug_pg_documents():

    return documents().get(
        "general_ug_pg",
        []
    )


def professional_documents():

    return documents().get(
        "additional_for_professional_programs",
        []
    )


def international_documents():

    return documents().get(
        "additional_for_nri_international",
        []
    )


# ---------------------------------------------------------
# Application Fee
# ---------------------------------------------------------

def application_fee():

    return _data().get(
        "application_fee_and_payment",
        {}
    )


# ---------------------------------------------------------
# Admission Types
# ---------------------------------------------------------

def admission_modes():

    return _data().get(
        "direct_vs_entrance_based_admission",
        {}
    )


# ---------------------------------------------------------
# International Admissions
# ---------------------------------------------------------

def international():

    return _data().get(
        "nri_and_international_admission",
        {}
    )


# ---------------------------------------------------------
# Lateral Entry
# ---------------------------------------------------------

def lateral_entry():

    return _data().get(
        "lateral_entry_admission",
        {}
    )


# ---------------------------------------------------------
# Quotas
# ---------------------------------------------------------

def quota_policy():

    return _data().get(
        "quota_policy",
        {}
    )


# ---------------------------------------------------------
# Transfer / Migration
# ---------------------------------------------------------

def transfer_policy():

    return _data().get(
        "transfer_and_migration_policy",
        {}
    )


# ---------------------------------------------------------
# Gap Year
# ---------------------------------------------------------

def gap_year():

    return _data().get(
        "gap_year_policy",
        {}
    )


# ---------------------------------------------------------
# Cancellation
# ---------------------------------------------------------

def cancellation_policy():

    return _data().get(
        "admission_cancellation_and_withdrawal",
        {}
    )


# ---------------------------------------------------------
# Summary
# ---------------------------------------------------------

def summary():

    return {

        "application_steps":

            len(application_steps()),

        "national_exams":

            len(national_exams()),

        "application_fee":

            application_fee().get(
                "amount_range"
            ),

        "payment_methods":

            application_fee().get(
                "payment_methods",
                []
            ),

        "quota_types":

            list(

                quota_policy().keys()

            )

    }


# ---------------------------------------------------------
# Statistics
# ---------------------------------------------------------

def statistics():

    return {

        "steps":

            len(application_steps()),

        "national_exams":

            len(national_exams()),

        "ug_documents":

            len(ug_pg_documents()),

        "professional_documents":

            len(professional_documents()),

        "international_documents":

            len(international_documents()),

        "quota_categories":

            len(quota_policy())

    }


# ---------------------------------------------------------
# Debug
# ---------------------------------------------------------

if __name__ == "__main__":

    print(summary())

    print()

    print(statistics())