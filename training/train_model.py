
# training/train_model.py
import json
import pickle
from itertools import product
from sklearn.feature_extraction.text import TfidfVectorizer
from unidecode import unidecode

def clean(s):
    return unidecode(s).strip()

def unique_preserve(seq):
    seen = set()
    out = []
    for x in seq:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out

# load data
with open("../data/college_data.json", "r", encoding="utf-8") as f:
    data = json.load(f)

questions = []
answers = []

# helper phrase pieces (lots of paraphrases)
q_prefixes_general = [
    "what is", "what are", "tell me about", "give information about", "give info about",
    "information about", "details of", "details about", "explain", "what can you tell me about"
]

q_prefixes_short = ["info", "about", "detail", "tell about"]

q_fee_words = ["fee", "fees", "cost", "price", "charges", "tuition", "tuition fee", "course fee", "yearly fee", "per year fee"]

q_wh = ["how much is", "how much does {} cost", "how expensive is", "what is the {} of", "what are the {} of"]

polite_suffixes = ["", " please", " please.", " asap", " now", " ?"]

# abbreviations map (add any domain-specific short forms)
abbr_map = {
    "b.tech": "B.Tech Computer Science Engineering",
    "btech": "B.Tech Computer Science Engineering",
    "bca": "BCA",
    "mba": "MBA",
    "bba": "BBA",
    "mech": "B.Tech Mechanical Engineering",
}

# --- FAQ direct entries ---
for item in data.get("faq", []):
    q = clean(item.get("question", ""))
    a = item.get("answer", "")
    if q:
        questions.append(q.lower())
        answers.append(a)

# --- University, contact ---
uni = data.get("university", "")
loc = data.get("location", "")
if uni:
    uni_phrases = [
        f"where is {uni}", f"{uni} location", "where is the university located",
        "which city is the university in", "location of the university", "where is the campus"
    ]
    for q in uni_phrases:
        questions.append(clean(q).lower()); answers.append(f"{uni} is located in {loc}.")

contact = data.get("contact", {})
if contact:
    questions += ["contact number", "university phone number", "university website", "university email"]
    answers += [contact.get("phone",""), contact.get("phone",""), contact.get("website",""), contact.get("email","")]

# Collect subjects: courses and their abbreviation variants
courses = data.get("courses", [])
course_names = []
for c in courses:
    name = c.get("course_name","").strip()
    if not name: continue
    variants = {name, name.lower()}
    # add abbreviation candidates if present in mapping
    lname = name.lower().replace(".", "").replace(" ", "")
    for abbr, full in abbr_map.items():
        if abbr.replace(".", "") in lname or abbr in lname:
            variants.add(abbr)
            variants.add(full)
    course_names.append( (name, c.get("fees_per_year"), c.get("duration"), list(variants)) )

# Hostels
hostels_boys = data.get("hostels_for_boys", [])
hostels_girls = data.get("hostels_for_girls", [])
all_hostels = hostels_boys + hostels_girls

# syntax generators (systematic)
# 1) Course questions: many fee/formats + info formats
course_fee_templates = []
# combine a set of prefixes and fee words to get many variations
for p, fee_word in product(
        ["what is", "what are", "tell me", "give me", "how much is", "how much are", "price of", "cost of", "what is the"],
        q_fee_words):
    # two useful forms:
    course_fee_templates.append(f"{p} {{x}} {fee_word}")
    course_fee_templates.append(f"{p} {fee_word} for {{x}}")
# also short forms
for s in q_prefixes_short:
    course_fee_templates.append(f"{s} {{x}} {q_fee_words[0]}")

# 2) Info templates
info_templates = []
for p in q_prefixes_general + q_prefixes_short:
    info_templates.append(f"{p} {{x}}")
    info_templates.append(f"{p} {{x}}?")

# 3) Hostels templates
hostel_templates = []
hostel_prefixes = ["tell me about", "what is", "what are", "information about", "details of", "hostel details for"]
for p in hostel_prefixes:
    hostel_templates.append(f"{p} {{x}} hostel")
    hostel_templates.append(f"{p} {{x}}")
for p in ["which hostels are for {x}", "list {x} hostels", "{x} hostels", "{x} wing hostels"]:
    hostel_templates.append(p)

# 4) Generic category templates (departments, facilities, admission, mess, library etc.)
category_templates = []
category_prefixes = ["what is", "what are", "tell me about", "give info about", "details of", "information about"]
for p in category_prefixes:
    category_templates.append(f"{p} {{x}}")
    category_templates.append(f"{p} {{x}}?")

# helper function for adding variants with polite suffixes
def add_variants(base_list, subject_text, answer_text):
    for base in base_list:
        for suf in polite_suffixes:
            questions.append(clean( (base.format(x=subject_text) + suf ) ).lower())
            answers.append(answer_text)

# Build course Q/A systematically
for name, fee, duration, variants in course_names:
    ans = f"{name} duration is {duration} and fee is ₹{fee} per year."
    for subj in variants:
        subj_clean = subj.strip()
        add_variants(info_templates, subj_clean, ans)
        add_variants(course_fee_templates, subj_clean, ans)
        # also add some wh- forms using {x} in position
        for wh in ["how much is {x}", "how much does {x} cost", "what is the cost of {x}", "price of {x}"]:
            for suf in polite_suffixes:
                questions.append(clean((wh.format(x=subj_clean) + suf)).lower())
                answers.append(ans)

# Build hostels Q/A systematically
for h in all_hostels:
    name = h.get("name", "").strip()
    fee = h.get("fees_per_year", "")
    sharing = h.get("sharing", "")
    ans = f"{name} hostel has {sharing} rooms and yearly fee is ₹{fee}."
    # generate many info and fee phrasing variants
    add_variants(info_templates + hostel_templates, name, ans)
    # include "boys/girls" phrasing variants
    if h in hostels_boys:
        add_variants(["boys hostel {x}", "male hostel {x}", "{x} boys hostel", "which hostels are for boys: {x}"], name, ans)
    else:
        add_variants(["girls hostel {x}", "female hostel {x}", "{x} girls hostel", "which hostels are for girls: {x}"], name, ans)

# Add aggregated/general questions for hostels (counts & facilities)
hostel_general_phrases = [
    "how many hostels", "total hostels", "number of hostels", "list all hostels", "all hostels",
    "hostel facilities", "what are the hostel facilities", "does hostel have wifi", "hostel wifi available"
]
for p in hostel_general_phrases:
    for suf in polite_suffixes:
        questions.append(clean((p + suf)).lower())
        answers.append("Hostel facilities include WiFi, laundry, housekeeping, RO water, and 24x7 security.")

# Departments
dept_list = ", ".join(data.get("departments", []))
if dept_list:
    for p in ["what departments are available", "list departments", "departments in university", "which departments"]:
        for suf in polite_suffixes:
            questions.append(clean((p + suf)).lower()); answers.append(f"The university has departments such as {dept_list}.")

# Admission
adm = data.get("admission", {})
adm_ans = f"Admission mode is {adm.get('application_mode','N/A')} and entrance exam includes {adm.get('entrance_exam','N/A')}. Admissions open during {adm.get('admission_open_month','N/A')}."
for p in ["how to get admission", "admission process", "university admission", "when are admissions open"]:
    for suf in polite_suffixes:
        questions.append(clean((p + suf)).lower()); answers.append(adm_ans)

# Mess & Library & Transport & Clubs & Campus timings
mess = data.get("mess", {})
if mess:
    for p,qans in [("mess timing", f"Mess timings are Breakfast {mess.get('breakfast_time')}, Lunch {mess.get('lunch_time')}, Dinner {mess.get('dinner_time')}."), 
                   ("breakfast time", f"{mess.get('breakfast_time')}"), ("lunch time", f"{mess.get('lunch_time')}"), ("dinner time", f"{mess.get('dinner_time')}")]:
        for suf in polite_suffixes:
            questions.append(clean((p + suf)).lower()); answers.append(qans)

lib = data.get("library", {})
if lib:
    for p,qans in [("library timing", f"Library opens at {lib.get('opening_time')} and closes at {lib.get('closing_time')}."), ("library opening time", f"{lib.get('opening_time')}"), ("library closing time", f"{lib.get('closing_time')}")]:
        for suf in polite_suffixes:
            questions.append(clean((p + suf)).lower()); answers.append(qans)

trans = data.get("transport", {})
if trans:
    for p in ["transport facility", "is transport available", "bus routes"]:
        for suf in polite_suffixes:
            questions.append(clean((p + suf)).lower()); answers.append(trans.get("bus_routes",""))

for club in data.get("clubs", []):
    for p in ["tell me about {x}", "information about {x}", "what is {x}"]:
        for suf in polite_suffixes:
            questions.append(clean((p.format(x=club) + suf)).lower()); answers.append(f"{club} is an active student club on campus.")

campus_t = data.get("campus_timing", {})
if campus_t:
    for p in ["campus timing", "what are campus timings"]:
        for suf in polite_suffixes:
            questions.append(clean((p + suf)).lower()); answers.append(f"Campus opens at {campus_t.get('opening')} and closes at {campus_t.get('closing')}.")

# --- Augment with short-fragment forms / typed variants (meaningful) ---
short_suffixes = ["", " pls", " plz", " pls.", " plz.", "?"]
short_prefixes = ["", "hey", "hi", "info", "can you tell me", "please tell me", "i want to know"]
# produce combinations for short forms of each base question to increase realistic variants
bases = list(questions)  # start from constructed meaningful Qs
for base in bases:
    # create a few compact/typed variants
    for pre in short_prefixes:
        for suf in short_suffixes:
            if pre:
                s = (pre + " " + base + suf).strip()
            else:
                s = (base + suf).strip()
            questions.append(clean(s).lower())
            # reuse existing answer by mapping: find index
            # find original index (may be slow but ok)
            # fallback: empty answer (shouldn't happen)
            # We'll append a generic helpful fallback if mapping fails
            answers.append(answers[bases.index(base)] if base in bases else "Please refer to university info.")

# Deduplicate while preserving order
questions = unique_preserve(questions)
# ensure answers align with deduped questions
# rebuild mapping: for each question find its first index in original list
orig_q_a = list(zip(bases, [answers[bases.index(b)] for b in bases]))
# but we previously appended many more answers; safe strategy: keep answers list aligned with questions earlier
# to be correct, we saved answers for each append, so we must dedupe pairs
pairs = []
seen = set()
full_pairs = list(zip(questions, [None]*len(questions)))  # placeholder
# Instead rebuild pairs using initial generation (we have 'answers' that already match original questions array length before dedupe)
# Since we appended answers parallelly to questions in every step above, we can simply dedupe pairs from original growing lists:
# Recreate lists in order: take the huge lists we created earlier in the same order (we still have them as variables)
# For simplicity, reload from the file that we just wrote pairs into: we kept questions and answers in parallel before dedupe, so we'll reconstruct as follows.

# The code above kept 'questions' and 'answers' parallel until dedupe; but we replaced questions with deduped list.
# To reconstruct answers aligned to deduped questions, iterate through original zipped (we still have original big lists in variables name 'questions' (now deduped) and 'answers' (big)).

# To avoid confusion, re-create original big lists by re-running generation lightly: simplest route is to load the full (questions, answers) pair from memory.
# But here we still have 'answers' parallel to the old big questions before we deduped into questions variable.
# We'll map using a dict from original big question->first answer occurrence.

# Rebuild mapping using data before dedupe: use 'answers' that currently map to old_questions (we saved old_questions into 'bases' earlier, but we appended many more questions after).
# So instead of overcomplicating, re-generate the mapping by re-building pairs using a second pass same as earlier (safe albeit duplicate work).

# For clarity and safety, we will re-run the generation into parallel lists 'full_q' and 'full_a' and then dedupe them preserving order.

full_q = []
full_a = []

# Re-run generator programmatically (repeat same steps deterministically) to fill full_q/full_a exactly the same as above.
# Because the above generation was deterministic (no randomness), re-executing yields same sequence.
# To keep code concise, I'll call a function to produce the full lists; but for readability, we will reconstruct by re-using the previously built lists: 
# At this point 'questions' is deduped; but we need answers matched: easiest approach is to store QA pairs during initial creation.
# To avoid too-long changes here, we will assume answers list remained parallel to created questions before dedupe (it did), so we can build mapping from original big list:
# We'll recreate original big list quickly by re-constructing 'full_q' and 'full_a' using the same loop logic (the code above).
# NOTE: in this file we kept the original 'answers' list appended in the same order as questions — so we can simply dedupe both in parallel:

# Deduplicate pairs in parallel:
seen = set()
q_final = []
a_final = []
# But we lost the original huge 'questions' list when we replaced it with deduped earlier - to avoid mistakes, reload the file and rebuild everything.
# To keep this script robust and deterministic, it's simpler to first generate parallel lists 'full_questions' and 'full_answers' from scratch in one place.
# For now, since we still have 'answers' with length >= deduped questions, we will dedupe pairs using a loop over indices:
# We'll reconstruct from raw pair accumulation by re-executing generation into full_questions/full_answers using same steps using a helper below.

# ---- Proper pair reconstruction (clean approach) ----

full_questions = []
full_answers = []

# We will reconstruct full lists by re-executing the above deterministic generators in the same order.
# (This duplicates code above but ensures pairs align.)

# ----- Start reconstruction -----
# Start with FAQ
for item in data.get("faq", []):
    q = clean(item.get("question", ""))
    a = item.get("answer", "")
    if q:
        full_questions.append(q.lower()); full_answers.append(a)

# uni/contact
if uni:
    for q in uni_phrases:
        full_questions.append(clean(q).lower()); full_answers.append(f"{uni} is located in {loc}.")
if contact:
    full_questions.extend(["contact number", "university phone number", "university website", "university email"])
    full_answers.extend([contact.get("phone",""), contact.get("phone",""), contact.get("website",""), contact.get("email","")])

# courses
for name, fee, duration, variants in course_names:
    ans = f"{name} duration is {duration} and fee is ₹{fee} per year."
    for subj in variants:
        subj_clean = subj.strip()
        for base in info_templates + course_fee_templates:
            for suf in polite_suffixes:
                full_questions.append(clean((base.format(x=subj_clean) + suf)).lower())
                full_answers.append(ans)
        for wh in ["how much is {x}", "how much does {x} cost", "what is the cost of {x}", "price of {x}"]:
            for suf in polite_suffixes:
                full_questions.append(clean((wh.format(x=subj_clean) + suf)).lower())
                full_answers.append(ans)

# hostels
for h in all_hostels:
    name = h.get("name", "").strip()
    fee = h.get("fees_per_year", "")
    sharing = h.get("sharing", "")
    ans = f"{name} hostel has {sharing} rooms and yearly fee is ₹{fee}."
    for base in info_templates + hostel_templates:
        for suf in polite_suffixes:
            full_questions.append(clean((base.format(x=name) + suf)).lower())
            full_answers.append(ans)
    if h in hostels_boys:
        for base in ["boys hostel {x}", "male hostel {x}", "{x} boys hostel"]:
            for suf in polite_suffixes:
                full_questions.append(clean((base.format(x=name) + suf)).lower()); full_answers.append(ans)
    else:
        for base in ["girls hostel {x}", "female hostel {x}", "{x} girls hostel"]:
            for suf in polite_suffixes:
                full_questions.append(clean((base.format(x=name) + suf)).lower()); full_answers.append(ans)

# hostel_general
for p in hostel_general_phrases:
    for suf in polite_suffixes:
        full_questions.append(clean((p + suf)).lower()); full_answers.append("Hostel facilities include WiFi, laundry, housekeeping, RO water, and 24x7 security.")

# departments
if dept_list:
    for p in ["what departments are available", "list departments", "departments in university", "which departments"]:
        for suf in polite_suffixes:
            full_questions.append(clean((p + suf)).lower()); full_answers.append(f"The university has departments such as {dept_list}.")

# admission
for p in ["how to get admission", "admission process", "university admission", "when are admissions open"]:
    for suf in polite_suffixes:
        full_questions.append(clean((p + suf)).lower()); full_answers.append(adm_ans)

# mess/library/transport/clubs/campus timing
if mess:
    for p,qans in [("mess timing", f"Mess timings are Breakfast {mess.get('breakfast_time')}, Lunch {mess.get('lunch_time')}, Dinner {mess.get('dinner_time')}."), 
                   ("breakfast time", f"{mess.get('breakfast_time')}"), ("lunch time", f"{mess.get('lunch_time')}"), ("dinner time", f"{mess.get('dinner_time')}")]:
        for suf in polite_suffixes:
            full_questions.append(clean((p + suf)).lower()); full_answers.append(qans)

if lib:
    for p,qans in [("library timing", f"Library opens at {lib.get('opening_time')} and closes at {lib.get('closing_time')}."), ("library opening time", f"{lib.get('opening_time')}"), ("library closing time", f"{lib.get('closing_time')}")]:
        for suf in polite_suffixes:
            full_questions.append(clean((p + suf)).lower()); full_answers.append(qans)

if trans:
    for p in ["transport facility", "is transport available", "bus routes"]:
        for suf in polite_suffixes:
            full_questions.append(clean((p + suf)).lower()); full_answers.append(trans.get("bus_routes",""))

for club in data.get("clubs", []):
    for p in ["tell me about {x}", "information about {x}", "what is {x}"]:
        for suf in polite_suffixes:
            full_questions.append(clean((p.format(x=club) + suf)).lower()); full_answers.append(f"{club} is an active student club on campus.")

if campus_t:
    for p in ["campus timing", "what are campus timings"]:
        for suf in polite_suffixes:
            full_questions.append(clean((p + suf)).lower()); full_answers.append(f"Campus opens at {campus_t.get('opening')} and closes at {campus_t.get('closing')}.")

# short typed variants
short_suffixes = ["", " pls", " plz", " pls.", " plz.", "?"]
short_prefixes = ["", "hey", "hi", "info", "can you tell me", "please tell me", "i want to know"]
for base_q, base_a in zip(list(full_questions), list(full_answers)):
    for pre in short_prefixes:
        for suf in short_suffixes:
            if pre:
                s = (pre + " " + base_q + suf).strip()
            else:
                s = (base_q + suf).strip()
            full_questions.append(clean(s).lower()); full_answers.append(base_a)

# Deduplicate preserving order
q_final = []
a_final = []
seen = set()
for q,a in zip(full_questions, full_answers):
    if q not in seen:
        seen.add(q)
        q_final.append(q)
        a_final.append(a)

questions = q_final
answers = a_final

print("Prepared training QA pairs:", len(questions))

# Build vectorizers: combination of word and char n-grams (robust to short/misspellings)
vec_word = TfidfVectorizer(ngram_range=(1,2), analyzer="word")
vec_char = TfidfVectorizer(ngram_range=(3,5), analyzer="char_wb")

Xw = vec_word.fit_transform(questions)
Xc = vec_char.fit_transform(questions)

from scipy.sparse import hstack
X = hstack([Xw, Xc])

# Save artifacts
import os
os.makedirs("../model", exist_ok=True)
pickle.dump(vec_word, open("../model/vectorizer_word.pkl", "wb"))
pickle.dump(vec_char, open("../model/vectorizer_char.pkl", "wb"))
pickle.dump(X, open("../model/model.pkl", "wb"))
pickle.dump(questions, open("../model/questions.pkl", "wb"))
pickle.dump(answers, open("../model/ans.pkl", "wb"))

print("Model trained and saved.")