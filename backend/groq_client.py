"""
groq_client.py

Production Groq Client

Responsibilities:
1. Build a rich context from retrieved documents.
2. Generate grounded answers.
3. Prevent hallucinations.
4. Merge information from multiple retrieved documents.
5. Produce natural conversational responses.
"""

import os
from dotenv import load_dotenv
from groq import Groq

# ---------------------------------------------------------
# LOAD ENVIRONMENT
# ---------------------------------------------------------

load_dotenv(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        ".env"
    )
)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise RuntimeError(
        "GROQ_API_KEY not found in .env"
    )

client = Groq(api_key=GROQ_API_KEY)

# ---------------------------------------------------------
# CONFIG
# ---------------------------------------------------------

MODEL_NAME = "llama-3.1-8b-instant"

TEMPERATURE = 0.0

MAX_TOKENS = 500

FALLBACK_SENTENCE = (
    "Sorry, I don't have that specific information. "
    "Please contact the university directly or check the official website."
)

# ---------------------------------------------------------
# SYSTEM PROMPT
# ---------------------------------------------------------

SYSTEM_PROMPT = f"""
You are Campus Genius, the official AI assistant for Parul University.

Your ONLY source of truth is the Knowledge Base supplied in the user message.

==================================================
RULES
==================================================

1.
Answer ONLY from the Knowledge Base.

Never use your own knowledge.

Never guess.

Never invent facts.

==================================================

2.
If multiple documents discuss the same topic,
combine them into ONE complete answer.

==================================================

3.
If the answer is a list
(specializations, hostels, facilities,
scholarships, departments, placements,
documents etc.)

ALWAYS return the COMPLETE list.

Never return only the first few items.

==================================================

4.
If the user asks multiple questions together,
answer every question that exists in the
Knowledge Base.

Ignore only the parts that truly cannot
be answered.

==================================================

5.
If absolutely nothing relevant exists,

reply EXACTLY:

"{FALLBACK_SENTENCE}"

Nothing else.

==================================================

6.
Never say:

"Based on the context"

"The provided information"

"The retrieved data"

"The context says"

"It is not mentioned"

"It is not specified"

"The knowledge base says"

These phrases are forbidden.

==================================================

7.
Write naturally.

Do not sound robotic.

==================================================

8.
If numerical values exist,
copy them exactly.

Never estimate.

==================================================

9.
If several retrieved documents contain
different pieces of one answer,
merge them into one response.

==================================================

10.
When appropriate,
use bullet lists.

==================================================

11.
If information is unavailable,

use ONLY the fallback sentence.

Do NOT explain why.
"""

# ---------------------------------------------------------
# CONTEXT BUILDING
# ---------------------------------------------------------

def _clean_text(text: str) -> str:
    """
    Remove unnecessary whitespace.
    """

    if not text:
        return ""

    return " ".join(str(text).split())


def _build_single_document(index: int, chunk: dict) -> str:
    """
    Convert one retrieved chunk into a structured document.
    """

    category = _clean_text(
        chunk.get("category", "General")
    )

    question = _clean_text(
        chunk.get("question", "")
    )

    answer = _clean_text(
        chunk.get("answer", "")
    )

    similarity = float(
        chunk.get("similarity", 0)
    )

    document = f"""
==============================
DOCUMENT {index}
==============================

Category:
{category}

Question:
{question}

Answer:
{answer}

Similarity:
{similarity:.3f}
"""

    return document.strip()


def build_context_block(chunks: list) -> str:
    """
    Build a rich context block.

    Every retrieved document is preserved so
    Groq can merge information across multiple
    documents instead of seeing only answers.
    """

    if not chunks:
        return ""

    documents = []

    seen_questions = set()

    for i, chunk in enumerate(chunks, start=1):

        question = (
            chunk.get("question", "")
            .strip()
            .lower()
        )

        if question in seen_questions:
            continue

        seen_questions.add(question)

        documents.append(
            _build_single_document(
                len(documents) + 1,
                chunk
            )
        )

    return "\n\n".join(documents)

# ---------------------------------------------------------
# USER PROMPT
# ---------------------------------------------------------

def build_user_prompt(
    user_question: str,
    chunks: list
) -> str:
    """
    Build the prompt that is sent to Groq.
    """

    context = build_context_block(chunks)

    return f"""
You are answering a student's question about Parul University.

==================================================
KNOWLEDGE BASE
==================================================

{context}

==================================================
STUDENT QUESTION
==================================================

{user_question}

==================================================
HOW TO ANSWER
==================================================

1.
Read ALL documents before answering.

2.
Merge information from every relevant document.

3.
If multiple documents describe the same course,
combine them into one complete answer.

4.
If the question asks for:

• Specializations

• Hostel names

• Facilities

• Courses

• Scholarships

• Placements

• Documents

• Eligibility

Always return the COMPLETE list.

Never stop after the first matching document.

5.
If the question asks for fees,
include every fee that belongs to the requested course.

6.
If multiple retrieved documents refer to the same course,
merge them naturally.

7.
Do NOT repeat the same sentence.

8.
Do NOT mention documents, context,
knowledge base, retrieval,
or provided information.

9.
If the answer does not exist anywhere,

reply EXACTLY:

{FALLBACK_SENTENCE}

10.
Return the answer in clean Markdown.

Use:

• Bullet lists

• Short paragraphs

• Tables if helpful

Never output JSON.

Never output XML.

Return ONLY the final answer.
"""

# ---------------------------------------------------------
# GROQ GENERATION
# ---------------------------------------------------------

def generate_answer(
    user_question: str,
    chunks: list
) -> str:
    """
    Generate a grounded answer using Groq.
    """

    if not chunks:
        return FALLBACK_SENTENCE

    prompt = build_user_prompt(
        user_question,
        chunks
    )

    try:

        response = client.chat.completions.create(

            model=MODEL_NAME,

            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],

            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
            top_p=1,
            stream=False,
        )

        answer = (
            response
            .choices[0]
            .message
            .content
            .strip()
        )

        if not answer:
            return FALLBACK_SENTENCE

        # -----------------------------------------
        # Clean unwanted phrases
        # -----------------------------------------

        replacements = {

            "Based on the context,": "",

            "Based on the provided information,": "",

            "Based on the information provided,": "",

            "According to the context,": "",

            "According to the provided information,": "",

            "The context states that": "",

            "The context says": "",

            "The provided information states that": "",

            "The provided information says": "",

            "From the context,": "",

            "From the information provided,": "",

        }

        for old, new in replacements.items():
            answer = answer.replace(old, new)

        # -----------------------------------------
        # Remove duplicate lines
        # -----------------------------------------

        cleaned_lines = []

        seen = set()

        for line in answer.splitlines():

            line = line.strip()

            if not line:
                continue

            key = line.lower()

            if key in seen:
                continue

            seen.add(key)

            cleaned_lines.append(line)

        answer = "\n".join(cleaned_lines).strip()

        if len(answer) < 5:
            return FALLBACK_SENTENCE

        return answer

    except Exception as e:

        print(f"[Groq Error] {e}")

        return (
            "Sorry, I'm currently unable to generate an answer. "
            "Please try again later."
        )

# ---------------------------------------------------------
# ANALYTICS FORMATTER
# ---------------------------------------------------------

def format_analytics_answer(
    user_question: str,
    structured_data
) -> str:
    """
    Convert structured analytics data into a natural answer.
    """

    prompt = f"""
You are Campus Genius, the official AI assistant of Parul University.

Answer ONLY using the structured information below.

Do not invent facts.

Question:
{user_question}

Structured Information:
{structured_data}

Write a natural, student-friendly answer.

Rules:
- Don't mention JSON.
- Don't mention structured data.
- Don't mention context.
- Use bullet points if needed.
- Return only the answer.
"""

    try:

        response = client.chat.completions.create(

            model=MODEL_NAME,

            messages=[
                {
                    "role": "system",
                    "content": "You are Campus Genius."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],

            temperature=0,

            max_tokens=MAX_TOKENS,

            stream=False

        )

        answer = response.choices[0].message.content.strip()

        if not answer:
            return str(structured_data)

        return answer

    except Exception:

        return str(structured_data)
    
# ---------------------------------------------------------
# MANUAL TEST
# ---------------------------------------------------------

if __name__ == "__main__":

    from retrieval import (
        retrieve,
        has_confident_match,
    )

    print("\n" + "=" * 60)
    print(" Campus Genius - Groq Client Test")
    print("=" * 60)
    print(f"Model        : {MODEL_NAME}")
    print(f"Temperature  : {TEMPERATURE}")
    print("=" * 60)

    while True:

        query = input("\nAsk > ").strip()

        if query.lower() in {"exit", "quit"}:
            break

        if not query:
            continue

        print("\nRetrieving documents...\n")

        chunks = retrieve(query)

        if not chunks:

            print(FALLBACK_SENTENCE)
            continue

        print("=" * 60)
        print(f"Retrieved {len(chunks)} document(s)")
        print("=" * 60)

        for i, chunk in enumerate(chunks, start=1):

            print(f"\nDocument {i}")

            print(f"Category   : {chunk.get('category','General')}")

            print(f"Similarity : {chunk.get('similarity',0):.3f}")

            print(f"Question   : {chunk.get('question','')}")

        print("\n" + "=" * 60)

        if not has_confident_match(chunks):

            print("\nLow confidence retrieval.\n")
            print(FALLBACK_SENTENCE)
            continue

        print("\nGenerating answer...\n")

        answer = generate_answer(
            query,
            chunks
        )

        print("=" * 60)
        print("FINAL ANSWER")
        print("=" * 60)

        print(answer)

        print("=" * 60)