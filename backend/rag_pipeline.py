"""
rag_pipeline.py

Main RAG pipeline for Campus Genius.

Flow
----
1. Greeting
2. Cache
3. Spell Correction / Query Cleanup   <-- now runs BEFORE routing
4. Structured Analytics
5. FAISS Retrieval
6. Groq Generation
7. Cache
8. Logging
"""

from retrieval import retrieve, has_confident_match, preprocess_query

from cache import get_cached_answer, set_cached_answer
from logger import log_interaction
from groq_client import (
    generate_answer,
    format_analytics_answer,
)

from analytics.router import route as analytics_route


UNIVERSITY_KEYWORDS = [
    "parul",
    "university",
    "course",
    "fee",
    "fees",
    "hostel",
    "faculty",
    "admission",
    "eligibility",
    "scholarship",
    "placement",
    "department",
    "campus",
    "college",
    "exam",
    "document",
]


def is_university_question(text: str) -> bool:
    """
    Soft relevance check. This is now only a *secondary* signal used
    to shape the fallback message — it is NOT used to hard-block a
    query, because that previously blocked misspelled / rephrased
    questions (e.g. "hostal") before they ever reached spell
    correction or the retrieval/confidence pipeline, which are much
    better judges of relevance than a fixed keyword list.
    """

    text = (text or "").lower()

    return any(k in text for k in UNIVERSITY_KEYWORDS)


FALLBACK_ANSWER = (
    "Sorry, I couldn't find reliable information for your question. "
    "Please contact Parul University or visit the official website."
)

GREETING_RESPONSES = {
    "hi": "Hello! 👋 I'm Campus Genius. Ask me anything about Parul University.",
    "hello": "Hello! 👋 I'm Campus Genius. How can I help you today?",
    "hey": "Hey! 👋 What would you like to know about Parul University?",
    "hii": "Hello! 👋 How can I help you today?",
    "hiii": "Hello! 👋 How can I help you today?",
    "good morning": "Good morning! ☀️ How can I help you today?",
    "good afternoon": "Good afternoon! How can I help you today?",
    "good evening": "Good evening! How can I help you today?",
    "thanks": "You're welcome! 😊",
    "thank you": "You're welcome! 😊",
    "thankyou": "You're welcome! 😊",
    "ok thanks": "You're welcome! 😊",
    "bye": "Goodbye! Have a great day.",
    "goodbye": "Goodbye! Feel free to ask again anytime.",
}


# --------------------------------------------------------
# Greeting
# --------------------------------------------------------

def check_greeting(text: str):

    if not text:
        return None

    normalized = text.strip().lower().strip("!.,?")

    return GREETING_RESPONSES.get(normalized)


# --------------------------------------------------------
# Analytics
# --------------------------------------------------------

def analytics_answer(user_question: str):

    result = analytics_route(user_question)

    if not result["handled"]:
        return None

    answer = format_analytics_answer(
        user_question,
        result["result"]
    )

    return answer


# --------------------------------------------------------
# Main
# --------------------------------------------------------

def get_answer(user_question: str):

    # --------------------------------------------------
    # Greeting (checked on raw text, before anything else)
    # --------------------------------------------------

    greeting = check_greeting(user_question)

    if greeting:

        log_interaction(
            question=user_question,
            chunks=[],
            answer=greeting,
            source="greeting"
        )

        return greeting

    # --------------------------------------------------
    # Cache (exact-match on raw text)
    # --------------------------------------------------

    cached = get_cached_answer(user_question)

    if cached:

        log_interaction(
            question=user_question,
            chunks=[],
            answer=cached,
            source="cache"
        )

        return cached

    # --------------------------------------------------
    # Spell correction + abbreviation expansion.
    # This is the key fix: everything downstream (analytics
    # routing, the university-relevance check, and retrieval)
    # now sees the CORRECTED query, not the raw typo'd one.
    # e.g. "hostal fecilities" -> "hostel facilities"
    # --------------------------------------------------

    corrected_question = preprocess_query(user_question)

    # --------------------------------------------------
    # Analytics (structured lookups: fees, hostel, course, etc.)
    # --------------------------------------------------

    analytics = analytics_answer(corrected_question)

    if analytics:

        set_cached_answer(
            user_question,
            analytics
        )

        log_interaction(
            question=user_question,
            chunks=[],
            answer=analytics,
            source="analytics"
        )

        return analytics

    # --------------------------------------------------
    # Relevance check (soft) — now runs on the CORRECTED
    # query, so a misspelled-but-relevant question no longer
    # gets rejected before retrieval even runs.
    # --------------------------------------------------

    if not is_university_question(corrected_question):

        log_interaction(
            question=user_question,
            chunks=[],
            answer=FALLBACK_ANSWER,
            source="off_topic"
        )

        return FALLBACK_ANSWER

    # --------------------------------------------------
    # Retrieval
    # --------------------------------------------------

    retrieved_chunks = retrieve(corrected_question)

    if not has_confident_match(retrieved_chunks):

        log_interaction(
            question=user_question,
            chunks=retrieved_chunks,
            answer=FALLBACK_ANSWER,
            source="no_match"
        )

        return FALLBACK_ANSWER

    # --------------------------------------------------
    # Groq
    # --------------------------------------------------

    try:

        final_answer = generate_answer(
            corrected_question,
            retrieved_chunks
        )

    except Exception as e:

        final_answer = (
            "Sorry, I'm temporarily unable to generate a response. "
            "Please try again in a few moments."
        )

        log_interaction(
            question=user_question,
            chunks=retrieved_chunks,
            answer=str(e),
            source="groq_error"
        )

        return final_answer

    # --------------------------------------------------
    # Cache (keyed on the ORIGINAL raw question, so the exact
    # same typo next time is an instant cache hit too)
    # --------------------------------------------------

    set_cached_answer(
        user_question,
        final_answer
    )

    # --------------------------------------------------
    # Log
    # --------------------------------------------------

    log_interaction(
        question=user_question,
        chunks=retrieved_chunks,
        answer=final_answer,
        source="groq"
    )

    return final_answer


# --------------------------------------------------------
# Debug
# --------------------------------------------------------

if __name__ == "__main__":

    while True:

        question = input("\nAsk: ")

        if question.lower() == "exit":
            break

        print("\nBot:\n")

        print(
            get_answer(question)
        )
