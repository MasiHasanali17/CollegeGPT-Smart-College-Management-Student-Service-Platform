import os
import re
import time
from datetime import timedelta

from flask import (
    Flask, render_template, request, jsonify,
    redirect, url_for, flash, session, send_file, abort
)
from flask_login import LoginManager, login_user, logout_user, login_required, current_user

from rag_pipeline import get_answer
from database import init_db
from auth import (
    get_student_by_id, register_student, verify_login,
    get_security_question, reset_password_with_security_answer,
    admin_reset_student_password, SECURITY_QUESTIONS
)

# Non-student (Interface 1) features — new, does not touch the chatbot
import prospective

# Current-student portal (Interface 2) features — new, does not touch the chatbot
import portal
import payments

# Phase 3 — scholarship checker, transport info
import scholarship_data
import campus_info

# Phase 4 — gallery, uploads, site search
import gallery
import uploads
import site_search

# Phase 5 — multi-role admin accounts, notifications
import admin_auth
import notifications

# Phase 6 — security utilities
import security

from analytics import course as course_analytics
from analytics import admission as admission_analytics
from analytics import fees as fees_analytics
from analytics import hostel as hostel_analytics

# Admin authentication is now real accounts with roles (see admin_auth.py /
# database.py ADMIN_ROLES). A default super_admin (superadmin / admin123)
# is auto-created on first run — see database.py _bootstrap_super_admin.

app = Flask(
    __name__,
    template_folder="../templates",
    static_folder="../static"
)

app.secret_key = security.get_or_create_secret_key()
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10MB upload limit (gallery/notice attachments)

# Session security (Phase 6)
app.config["SESSION_COOKIE_HTTPONLY"] = True   # JS can't read the session cookie
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"  # baseline CSRF defense: cookie isn't sent on cross-site POSTs
app.permanent_session_lifetime = timedelta(days=7)

ADMIN_SESSION_MAX_AGE = timedelta(hours=3)  # admin sessions expire sooner than student ones

# Performance (Phase 6): gzip-compress text responses (HTML/CSS/JS/JSON)
try:
    from flask_compress import Compress
    Compress(app)
except ImportError:
    pass  # flask-compress not installed — app still works, just without gzip


@app.after_request
def set_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    # Static assets (CSS/JS/uploaded images/PDFs) are safe to cache
    # aggressively — uploaded files get a random UUID prefix per file,
    # so a new upload never collides with/serves a stale cached one.
    if request.path.startswith("/static/"):
        response.headers["Cache-Control"] = "public, max-age=604800"  # 7 days

    return response


@app.context_processor
def inject_csrf_token():
    return {"csrf_token": lambda: security.generate_csrf_token(session)}


CSRF_EXEMPT_ENDPOINTS = {
    "ask",                  # chatbot — must not require changes to chatbot.html/js
    "login",                # login forms: CSRF here isn't the relevant threat model
    "admin_login",          # (worst case is self-submitting your own credentials);
                             # session-bound token also wouldn't exist pre-login yet
    "forgot_password",      # not session-authenticated at all — protected by rate
                             # limiting on the security-answer step instead, since
                             # CSRF tokens don't stop a direct attacker call anyway
    "admission_track",      # read-only lookup, no state change
    "api_scholarship_check",  # AJAX/JSON — read-only computation, no state change
}
# Note: contact_submit, portal_create_order, and portal_verify_payment are
# AJAX/JSON endpoints that DO mutate state (save a message / touch payment
# flow), so they are NOT exempt — their JS sends the token via the
# X-CSRFToken header instead of a form field (see base.html's meta tag).


@app.before_request
def enforce_csrf():
    if request.method != "POST":
        return None

    if request.endpoint in CSRF_EXEMPT_ENDPOINTS:
        return None

    submitted = request.form.get("csrf_token") or request.headers.get("X-CSRFToken", "")

    if not security.validate_csrf_token(session, submitted):
        flash("Your session expired or the form was resubmitted. Please try again.")
        return redirect(request.referrer or url_for("home"))

    return None

# Initialize database
init_db()

# Flask Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


@login_manager.user_loader
def load_user(user_id):
    return get_student_by_id(user_id)


# ====================================================
# ENTRY PAGE
# ====================================================

@app.route("/")
def welcome():
    return render_template("welcome.html")


# ====================================================
# PUBLIC WEBSITE (VISITOR)
# ====================================================

@app.route("/visitor")
def home():
    return render_template("index.html")


@app.route("/chatbot")
def chatbot_page():
    return render_template("chatbot.html")


@app.route("/courses")
def courses():
    return render_template("courses.html")


@app.route("/placements")
def placements():
    return render_template("placements.html")


@app.route("/achievements")
def achievements():
    return render_template("achievements.html")


@app.route("/why")
def why():
    return render_template("why.html")


@app.route("/faq")
def faq():
    return render_template("faq.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


@app.route("/contact/submit", methods=["POST"])
def contact_submit():
    data = request.get_json(silent=True) or request.form

    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip()
    subject = (data.get("subject") or "").strip()
    message = (data.get("message") or "").strip()

    if not name or not email or not message:
        return jsonify({"ok": False, "error": "Name, email and message are required."}), 400

    prospective.save_contact_message(name, email, subject, message)

    return jsonify({"ok": True, "message": "Thanks! Your message has been received."})


@app.route("/compare")
def compare():
    return render_template("compare.html", courses=course_analytics.course_names())


@app.route("/api/course-details")
def api_course_details():
    course_name = request.args.get("course", "").strip()

    if not course_name:
        return jsonify({"ok": False, "error": "No course specified."}), 400

    details = course_analytics.details(course_name)

    if not details:
        return jsonify({"ok": False, "error": "Course not found."}), 404

    specializations = details.get("specializations") or []
    spec_names = [s.get("name") for s in specializations if isinstance(s, dict) and s.get("name")]

    return jsonify({
        "ok": True,
        "course_name": details.get("course_name", course_name),
        "duration": details.get("duration", "-"),
        "program_type": details.get("program_type", "-"),
        "faculty": details.get("faculty_name", "-"),
        "fee_text": course_analytics.tuition_fee(course_name) or "Contact admissions",
        "specializations": spec_names[:6],
        "specializations_more": max(0, len(spec_names) - 6),
    })


@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json()
    question = data.get("question", "")
    answer = get_answer(question)
    return jsonify({"answer": answer})


# ====================================================
# NON-STUDENT (PROSPECTIVE STUDENT) FEATURES
# ====================================================

@app.route("/campus-tour")
def campus_tour():
    return render_template("campus_tour.html")


@app.route("/campus-life")
def campus_life():
    return render_template("campus_life.html")


@app.route("/brochure")
def brochure():
    brochure_path = os.path.join(
        os.path.dirname(__file__), "..", "static", "brochure",
        "Parul_University_Brochure.pdf"
    )

    if not os.path.exists(brochure_path):
        abort(404)

    return send_file(
        brochure_path,
        as_attachment=True,
        download_name="Parul_University_Brochure.pdf"
    )


# --- Fee Calculator -------------------------------------------------

@app.route("/fee-calculator")
def fee_calculator():
    return render_template(
        "fee_calculator.html",
        courses=course_analytics.course_names()
    )


@app.route("/api/fee-estimate")
def api_fee_estimate():
    course_name = request.args.get("course", "").strip()

    if not course_name:
        return jsonify({"ok": False, "error": "No course selected."}), 400

    fee_text = course_analytics.tuition_fee(course_name)
    duration_text = course_analytics.duration(course_name)

    if not fee_text:
        return jsonify({
            "ok": False,
            "error": "Fee data not available for this course. Please ask the chatbot or contact admissions."
        })

    yearly_amount = fees_analytics._extract_amount(fee_text)

    years_match = re.search(r"(\d+)", duration_text or "")
    years = int(years_match.group(1)) if years_match else None

    total_amount = (
        yearly_amount * years
        if (yearly_amount and years) else None
    )

    return jsonify({
        "ok": True,
        "course": course_name,
        "duration": duration_text,
        "fee_text": fee_text,
        "yearly_amount": yearly_amount,
        "years": years,
        "total_amount": total_amount
    })


# --- Eligibility Checker ---------------------------------------------

@app.route("/eligibility-checker")
def eligibility_checker():
    return render_template(
        "eligibility_checker.html",
        courses=course_analytics.course_names()
    )


# --- Admission Process, Application & Tracking -----------------------

@app.route("/admission")
def admission():
    return render_template(
        "admission.html",
        steps=admission_analytics.application_steps(),
        documents=admission_analytics.documents(),
        courses=course_analytics.course_names()
    )


@app.route("/admission/apply", methods=["POST"])
def admission_apply():
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    phone = request.form.get("phone", "").strip()
    course_name = request.form.get("course", "").strip()

    if not name or not email or not course_name:
        flash("Please fill all required fields.")
        return redirect(url_for("admission"))

    tracking_id = prospective.create_application(name, email, phone, course_name)

    return render_template(
        "admission.html",
        steps=admission_analytics.application_steps(),
        documents=admission_analytics.documents(),
        courses=course_analytics.course_names(),
        new_tracking_id=tracking_id
    )


@app.route("/admission/track", methods=["GET", "POST"])
def admission_track():
    result = None
    searched = False

    if request.method == "POST":
        searched = True
        tracking_id = request.form.get("tracking_id", "").strip()
        result = prospective.get_application(tracking_id)

    return render_template(
        "track_application.html",
        result=result,
        searched=searched
    )


# --- Scholarship Checker (Phase 3) ------------------------------------

@app.route("/scholarship-checker")
def scholarship_checker():
    return render_template("scholarship_checker.html")


@app.route("/api/scholarship-check", methods=["POST"])
def api_scholarship_check():
    data = request.get_json(silent=True) or {}

    def to_float(v):
        try:
            return float(v)
        except (TypeError, ValueError):
            return None

    matches = scholarship_data.check_eligibility(
        percentage=to_float(data.get("percentage")),
        category=(data.get("category") or "").strip().lower(),
        sports_achiever=bool(data.get("sports_achiever")),
        defense_ward=bool(data.get("defense_ward")),
        income_lakh=to_float(data.get("income_lakh")),
    )

    return jsonify({
        "ok": True,
        "matches": matches,
        "general_note": scholarship_data.GENERAL_NOTE,
        "count": len(matches)
    })


# --- Hostel Information (Phase 3, real data) --------------------------

@app.route("/hostel-info")
def hostel_info():
    return render_template(
        "hostel_info.html",
        all_hostels=hostel_analytics.all_hostels(),
        boys_names=hostel_analytics.boys_hostel_names(),
        girls_names=hostel_analytics.girls_hostel_names(),
        facilities=hostel_analytics.facilities(),
        mess=hostel_analytics.mess(),
        wifi=hostel_analytics.wifi(),
        laundry=hostel_analytics.laundry(),
        water_supply=hostel_analytics.water_supply(),
        allotment=hostel_analytics.allotment(),
        cheapest=hostel_analytics.lowest_fee(),
        costliest=hostel_analytics.highest_fee(),
    )


# --- Transport Information (Phase 3, admin-manageable) -----------------

@app.route("/transport")
def transport():
    return render_template("transport.html", routes=campus_info.list_routes())


# --- Gallery (Phase 4, admin-manageable) --------------------------------

@app.route("/gallery")
def gallery_page():
    category = request.args.get("category", "All")
    return render_template(
        "gallery.html",
        images=gallery.list_images(category),
        categories=gallery.CATEGORIES,
        active_category=category
    )


# --- Site Search (Phase 4) ----------------------------------------------

@app.route("/search")
def search():
    query = request.args.get("q", "")
    results = site_search.search(query)
    return render_template("search_results.html", results=results)


# --- Simple Admin Panel for Applications ------------------------------

def current_admin():
    """
    Looks up the logged-in admin fresh from the DB each time (not just
    trusting the session blindly), so a deactivated account is locked
    out immediately even mid-session. Also enforces a shorter session
    lifetime for admin sessions than student sessions, since these are
    higher-privilege accounts.
    """

    admin_id = session.get("admin_id")

    if not admin_id:
        return None

    login_time = session.get("admin_login_time")
    if login_time and (time.time() - login_time) > ADMIN_SESSION_MAX_AGE.total_seconds():
        session.pop("admin_id", None)
        session.pop("admin_role", None)
        session.pop("admin_username", None)
        session.pop("admin_login_time", None)
        return None

    admin = admin_auth.get_admin_by_id(admin_id)

    if not admin or not admin["active"]:
        session.pop("admin_id", None)
        session.pop("admin_role", None)
        session.pop("admin_username", None)
        return None

    return admin


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        rl_key = f"admin_login:{request.remote_addr}:{username.lower()}"

        if security.is_locked_out(rl_key):
            wait = security.seconds_until_unlock(rl_key)
            flash(f"Too many failed attempts. Try again in {wait // 60 + 1} minute(s).")
            return redirect(url_for("admin_login", next=request.args.get("next", "")))

        admin = admin_auth.verify_admin_login(username, password)

        if not admin:
            security.record_failed_attempt(rl_key)
            flash("Incorrect username or password.")
            return redirect(url_for("admin_login", next=request.args.get("next", "")))

        security.clear_attempts(rl_key)

        session["admin_id"] = admin["id"]
        session["admin_role"] = admin["role"]
        session["admin_username"] = admin["username"]
        session["admin_login_time"] = time.time()

        next_url = request.args.get("next") or url_for("admin_portal")
        return redirect(next_url)

    return render_template("admin_login.html")


@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_id", None)
    session.pop("admin_role", None)
    session.pop("admin_username", None)
    return redirect(url_for("admin_login"))


@app.route("/admin/applications", methods=["GET", "POST"])
def admin_applications():

    admin = current_admin()

    if not admin:
        return redirect(url_for("admin_login", next=url_for("admin_applications")))

    if not admin_auth.can_access(admin["role"], "applications"):
        flash("Your admin role doesn't have access to Applications.")
        return redirect(url_for("admin_portal"))

    if request.method == "POST" and "status_update" in request.form:
        tid = request.form.get("tracking_id", "")
        new_status = request.form.get("status_update", "")
        prospective.update_application_status(tid, new_status)
        return redirect(url_for("admin_applications"))

    return render_template(
        "admin_applications.html",
        logged_in=True,
        admin=admin,
        applications=prospective.list_applications(),
        statuses=prospective.APPLICATION_STATUSES
    )


# ====================================================
# STUDENT AUTHENTICATION
# ====================================================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        student_id = request.form.get("student_id", "").strip()
        name = request.form.get("name", "").strip()
        password = request.form.get("password", "")
        course = request.form.get("course", "").strip()
        security_question = request.form.get("security_question", "").strip()
        security_answer = request.form.get("security_answer", "").strip()

        if not student_id or not name or not password:
            flash("Please fill all required fields.")
            return redirect(url_for("register"))

        if not security.is_strong_enough_password(password):
            flash(f"Password should be at least {security.MIN_PASSWORD_LENGTH} characters.")
            return redirect(url_for("register"))

        success, message = register_student(
            student_id,
            name,
            password,
            course,
            security_question=security_question or None,
            security_answer=security_answer or None
        )

        if not success:
            flash(message)
            return redirect(url_for("register"))

        flash("Registration successful. Please log in.")
        return redirect(url_for("login"))

    return render_template("register.html", security_questions=SECURITY_QUESTIONS)


@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        student_id = request.form.get("student_id", "").strip()
        password = request.form.get("password", "")

        rl_key = f"student_login:{request.remote_addr}:{student_id.lower()}"

        if security.is_locked_out(rl_key):
            wait = security.seconds_until_unlock(rl_key)
            flash(f"Too many failed attempts. Try again in {wait // 60 + 1} minute(s).")
            return redirect(url_for("login"))

        student = verify_login(
            student_id,
            password
        )

        if not student:
            security.record_failed_attempt(rl_key)
            flash("Invalid student ID or password.")
            return redirect(url_for("login"))

        security.clear_attempts(rl_key)

        login_user(student)
        return redirect(url_for("dashboard"))

    return render_template("login.html")


@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    """
    Security-question-based reset. No real email/SMS service is
    configured in this project, so rather than fake an "email sent"
    flow that doesn't actually send anything, this is the honest,
    actually-working option. (Admin-assisted reset is also available
    via the Student Services admin panel for students who never set
    a security question.)
    """

    step = request.form.get("step", "find")
    student_id = request.form.get("student_id", "").strip()
    question = None

    if request.method == "POST" and step == "find":
        question = get_security_question(student_id)
        if not question:
            flash("No security question found for that Student ID. Ask admin for help resetting your password.")
            return redirect(url_for("forgot_password"))

    elif request.method == "POST" and step == "reset":
        answer = request.form.get("security_answer", "")
        new_password = request.form.get("new_password", "")

        rl_key = f"forgot_password:{request.remote_addr}:{student_id.lower()}"

        if security.is_locked_out(rl_key):
            wait = security.seconds_until_unlock(rl_key)
            flash(f"Too many attempts. Try again in {wait // 60 + 1} minute(s).")
            return redirect(url_for("forgot_password"))

        if not security.is_strong_enough_password(new_password):
            flash(f"New password should be at least {security.MIN_PASSWORD_LENGTH} characters.")
            question = get_security_question(student_id)
            return render_template("forgot_password.html", question=question, student_id=student_id)

        success, message = reset_password_with_security_answer(student_id, answer, new_password)

        if not success:
            security.record_failed_attempt(rl_key)
        else:
            security.clear_attempts(rl_key)

        flash(message)

        if success:
            return redirect(url_for("login"))

        question = get_security_question(student_id)

    return render_template("forgot_password.html", question=question, student_id=student_id)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("welcome"))


# ====================================================
# STUDENT DASHBOARD
# ====================================================

@app.route("/dashboard")
@login_required
def dashboard():
    sid = current_user.student_id

    return render_template(
        "dashboard.html",
        student=current_user,
        notice_count=len(portal.list_notices()),
        upcoming_events=portal.list_activities("event")[:3],
        my_hostel_requests=portal.list_hostel_requests_for_student(sid),
        my_grievances=portal.list_grievances_for_student(sid),
    )


# ====================================================
# STUDENT PORTAL (INTERFACE 2) — NOTICES
# ====================================================

@app.route("/portal/notices")
@login_required
def portal_notices():
    category = request.args.get("category", "All")
    return render_template(
        "portal_notices.html",
        notices=portal.list_notices(category),
        active_category=category
    )


# ====================================================
# STUDENT PORTAL — ACTIVITIES (events / courses / facilities)
# ====================================================

ACTIVITY_PAGE_INFO = {
    "event": {
        "template": "portal_events.html",
        "endpoint": "portal_events",
        "verb": "booked",
    },
    "course": {
        "template": "portal_courses.html",
        "endpoint": "portal_courses",
        "verb": "registered",
    },
    "facility": {
        "template": "portal_facilities.html",
        "endpoint": "portal_facilities",
        "verb": "booked",
    },
}


@app.route("/portal/events")
@login_required
def portal_events():
    sid = current_user.student_id
    return render_template(
        "portal_events.html",
        activities=portal.list_activities("event"),
        booked_ids=portal.get_student_booked_activity_ids(sid, "event")
    )


@app.route("/portal/courses")
@login_required
def portal_courses():
    sid = current_user.student_id
    return render_template(
        "portal_courses.html",
        activities=portal.list_activities("course"),
        booked_ids=portal.get_student_booked_activity_ids(sid, "course")
    )


@app.route("/portal/facilities")
@login_required
def portal_facilities():
    sid = current_user.student_id
    return render_template(
        "portal_facilities.html",
        activities=portal.list_activities("facility"),
        booked_ids=portal.get_student_booked_activity_ids(sid, "facility")
    )


@app.route("/portal/book/<int:activity_id>", methods=["POST"])
@login_required
def portal_book(activity_id):
    activity = portal.get_activity(activity_id)

    if not activity:
        flash("This is no longer available.")
        return redirect(url_for("dashboard"))

    info = ACTIVITY_PAGE_INFO[activity["kind"]]

    # Paid activities go through Razorpay checkout instead of instant booking
    if activity["price"] and activity["price"] > 0:
        return redirect(url_for("portal_checkout", activity_id=activity_id))

    success, result = portal.book_activity(
        activity_id,
        current_user.student_id,
        current_user.name
    )

    if success:
        # `result` is the booking_ref on success — take them straight to their ticket
        return redirect(url_for("portal_ticket", booking_ref=result))

    flash(result)
    return redirect(url_for(info["endpoint"]))


@app.route("/portal/cancel/<int:activity_id>", methods=["POST"])
@login_required
def portal_cancel(activity_id):
    activity = portal.get_activity(activity_id)

    if not activity:
        return redirect(url_for("dashboard"))

    info = ACTIVITY_PAGE_INFO[activity["kind"]]

    my_bookings = portal.list_bookings_for_student(current_user.student_id)
    this_booking = next((b for b in my_bookings if b["activity_id"] == activity_id), None)

    if this_booking and this_booking["payment_status"] == "paid":
        flash("This was a paid booking — please contact admissions for cancellation/refund instead of cancelling here.")
        return redirect(url_for(info["endpoint"]))

    portal.cancel_booking(activity_id, current_user.student_id)
    flash("Cancelled.")
    return redirect(url_for(info["endpoint"]))


# --- Paid checkout flow (Razorpay) -----------------------------------

@app.route("/portal/checkout/<int:activity_id>")
@login_required
def portal_checkout(activity_id):
    activity = portal.get_activity(activity_id)

    if not activity or not activity["price"]:
        flash("This item doesn't require payment.")
        return redirect(url_for("dashboard"))

    info = ACTIVITY_PAGE_INFO[activity["kind"]]
    already_booked = activity_id in portal.get_student_booked_activity_ids(
        current_user.student_id, activity["kind"]
    )

    if already_booked:
        flash("You've already booked this.")
        return redirect(url_for(info["endpoint"]))

    return render_template(
        "portal_checkout.html",
        activity=activity,
        payments_configured=payments.is_configured()
    )


@app.route("/portal/create-order/<int:activity_id>", methods=["POST"])
@login_required
def portal_create_order(activity_id):
    activity = portal.get_activity(activity_id)

    if not activity:
        return jsonify({"ok": False, "error": "Not available."}), 404

    if not activity["price"] or activity["price"] <= 0:
        return jsonify({"ok": False, "error": "This item is free — no payment needed."}), 400

    if activity_id in portal.get_student_booked_activity_ids(current_user.student_id, activity["kind"]):
        return jsonify({"ok": False, "error": "You've already booked this."}), 400

    if activity["capacity"]:
        booked_count = len(portal.list_bookings_for_activity(activity_id))
        if booked_count >= activity["capacity"]:
            return jsonify({"ok": False, "error": "Sorry, this is now full."}), 400

    order, error = payments.create_order(
        activity["price"],
        receipt=f"act{activity_id}_{current_user.student_id}"[:40]
    )

    if error:
        return jsonify({"ok": False, "error": error}), 400

    portal.create_payment_order_record(
        order["id"], activity_id, current_user.student_id, current_user.name, activity["price"]
    )

    return jsonify({
        "ok": True,
        "order_id": order["id"],
        "amount": order["amount"],
        "currency": order["currency"],
        "key_id": payments.RAZORPAY_KEY_ID,
        "activity_title": activity["title"],
        "student_name": current_user.name,
    })


@app.route("/portal/verify-payment", methods=["POST"])
@login_required
def portal_verify_payment():
    data = request.get_json(silent=True) or {}

    order_id = data.get("razorpay_order_id", "")
    payment_id = data.get("razorpay_payment_id", "")
    signature = data.get("razorpay_signature", "")

    if not (order_id and payment_id and signature):
        return jsonify({"ok": False, "error": "Missing payment details."}), 400

    if not payments.verify_signature(order_id, payment_id, signature):
        return jsonify({"ok": False, "error": "Payment verification failed."}), 400

    order_record = portal.get_payment_order(order_id)

    if not order_record:
        return jsonify({"ok": False, "error": "Order not found."}), 404

    if order_record["student_id"] != current_user.student_id:
        return jsonify({"ok": False, "error": "This order doesn't belong to you."}), 403

    success, result = portal.book_activity(
        order_record["activity_id"],
        order_record["student_id"],
        order_record["student_name"],
        payment_status="paid",
        amount_paid=order_record["amount"],
        razorpay_payment_id=payment_id
    )

    if not success:
        portal.mark_payment_order_status(order_id, "failed")
        return jsonify({
            "ok": False,
            "error": f"Payment received but booking failed ({result}). Please contact admissions for a refund."
        }), 409

    portal.mark_payment_order_status(order_id, "paid")

    return jsonify({
        "ok": True,
        "booking_ref": result,
        "redirect": url_for("portal_ticket", booking_ref=result)
    })


# --- Ticket / My Bookings ---------------------------------------------

@app.route("/portal/ticket/<booking_ref>")
@login_required
def portal_ticket(booking_ref):
    booking = portal.get_booking_by_ref(booking_ref)

    if not booking or booking["student_id"] != current_user.student_id:
        flash("Ticket not found.")
        return redirect(url_for("portal_my_bookings"))

    qr_code = portal.generate_ticket_qr_base64(booking_ref)

    return render_template("portal_ticket.html", booking=booking, qr_code=qr_code)


@app.route("/portal/my-bookings")
@login_required
def portal_my_bookings():
    return render_template(
        "portal_my_bookings.html",
        bookings=portal.list_bookings_for_student(current_user.student_id)
    )


# ====================================================
# STUDENT PORTAL — HOSTEL TRANSFER REQUEST
# ====================================================

@app.route("/portal/hostel-transfer", methods=["GET", "POST"])
@login_required
def portal_hostel_transfer():
    if request.method == "POST":
        portal.create_hostel_transfer_request(
            current_user.student_id,
            current_user.name,
            request.form.get("current_hostel", "").strip(),
            request.form.get("requested_hostel", "").strip(),
            request.form.get("reason", "").strip(),
            request.form.get("refund_needed", "No")
        )
        flash("Your hostel transfer request has been submitted.")
        return redirect(url_for("portal_hostel_transfer"))

    return render_template(
        "portal_hostel_transfer.html",
        requests=portal.list_hostel_requests_for_student(current_user.student_id)
    )


# ====================================================
# STUDENT PORTAL — GRIEVANCE / COMPLAINT DESK
# ====================================================

@app.route("/portal/grievance", methods=["GET", "POST"])
@login_required
def portal_grievance():
    if request.method == "POST":
        portal.create_grievance(
            current_user.student_id,
            current_user.name,
            request.form.get("category", "").strip(),
            request.form.get("description", "").strip()
        )
        flash("Your complaint has been submitted.")
        return redirect(url_for("portal_grievance"))

    return render_template(
        "portal_grievance.html",
        grievances=portal.list_grievances_for_student(current_user.student_id)
    )


# ====================================================
# STUDENT PORTAL — ACADEMIC RECORDS
# ====================================================

@app.route("/portal/academics")
@login_required
def portal_academics():
    return render_template(
        "portal_academics.html",
        record=portal.get_academic_record(current_user.student_id)
    )


# ====================================================
# STUDENT PORTAL — NOTIFICATIONS (bell icon)
# ====================================================

@app.route("/portal/notifications")
@login_required
def portal_notifications():
    notifications.mark_all_read(current_user.student_id)
    return render_template(
        "portal_notifications.html",
        items=notifications.list_notifications(current_user.student_id)
    )


@app.route("/api/notifications/unread-count")
@login_required
def api_unread_notifications():
    return jsonify({"count": notifications.unread_count(current_user.student_id)})


# ====================================================
# UNIFIED STAFF ADMIN PANEL FOR THE STUDENT PORTAL
# ====================================================

@app.route("/admin/portal", methods=["GET", "POST"])
def admin_portal():

    admin = current_admin()

    if not admin:
        return redirect(url_for("admin_login", next=url_for("admin_portal")))

    my_tabs = admin_auth.allowed_tabs(admin["role"])

    if not my_tabs:
        flash("Your admin account doesn't have access to any sections yet. Contact a super admin.")
        return redirect(url_for("admin_login"))

    tab = request.args.get("tab", my_tabs[0])

    if not admin_auth.can_access(admin["role"], tab):
        flash("You don't have permission to access that section.")
        return redirect(url_for("admin_portal", tab=my_tabs[0]))

    if request.method == "POST":
        action = request.form.get("action", "")

        if action == "create_notice":
            attachment_filename = uploads.save_upload(
                request.files.get("attachment"),
                "notices",
                uploads.ALLOWED_DOC_EXT
            )
            portal.create_notice(
                request.form.get("title", "").strip(),
                request.form.get("category", "General").strip(),
                request.form.get("description", "").strip(),
                expiry_date=request.form.get("expiry_date", "").strip() or None,
                target_audience=request.form.get("target_audience", "All Students").strip(),
                attachment_filename=attachment_filename
            )

        elif action == "delete_notice":
            portal.delete_notice(int(request.form.get("notice_id")))

        elif action == "upload_image":
            filename = uploads.save_upload(
                request.files.get("image"),
                "gallery",
                uploads.ALLOWED_IMAGE_EXT,
                optimize=True
            )
            if filename:
                gallery.add_image(
                    request.form.get("category", "Campus"),
                    request.form.get("caption", "").strip(),
                    filename
                )
            else:
                flash("Please upload a valid image file (jpg, jpeg, png, webp, or gif).")

        elif action == "delete_image":
            image_id = int(request.form.get("image_id"))
            image = gallery.get_image(image_id)
            if image:
                uploads.delete_upload(image["filename"], "gallery")
            gallery.delete_image(image_id)

        elif action == "create_activity":
            portal.create_activity(
                request.form.get("kind"),
                request.form.get("title", "").strip(),
                request.form.get("description", "").strip(),
                request.form.get("schedule_text", "").strip(),
                int(request.form.get("capacity") or 0),
                int(request.form.get("price") or 0)
            )

        elif action == "delete_activity":
            portal.delete_activity(int(request.form.get("activity_id")))

        elif action == "update_hostel_status":
            request_id = int(request.form.get("request_id"))
            new_status = request.form.get("status")
            record = portal.get_hostel_request(request_id)
            portal.update_hostel_request_status(request_id, new_status)
            if record:
                notifications.create_notification(
                    record["student_id"],
                    f"Your hostel transfer request ({record['current_hostel']} → "
                    f"{record['requested_hostel']}) is now: {new_status}",
                    link="/portal/hostel-transfer"
                )

        elif action == "update_grievance_status":
            grievance_id = int(request.form.get("grievance_id"))
            new_status = request.form.get("status")
            record = portal.get_grievance(grievance_id)
            portal.update_grievance_status(grievance_id, new_status)
            if record:
                notifications.create_notification(
                    record["student_id"],
                    f"Your complaint ({record['category']}) status changed to: {new_status}",
                    link="/portal/grievance"
                )

        elif action == "update_academic":
            student_id = request.form.get("student_id")
            portal.upsert_academic_record(
                student_id,
                request.form.get("attendance_percent", "-").strip(),
                request.form.get("exam_timetable", "").strip(),
                request.form.get("results", "").strip()
            )
            notifications.create_notification(
                student_id,
                "Your academic records have been updated.",
                link="/portal/academics"
            )

        elif action == "create_route":
            campus_info.create_route(
                request.form.get("route_name", "").strip(),
                request.form.get("stops_text", "").strip(),
                request.form.get("timing_text", "").strip(),
                request.form.get("contact", "").strip()
            )

        elif action == "delete_route":
            campus_info.delete_route(int(request.form.get("route_id")))

        elif action == "reset_student_password":
            new_pw = request.form.get("new_password", "").strip()
            target_student_id = request.form.get("student_id", "").strip()
            if not security.is_strong_enough_password(new_pw):
                flash(f"Password should be at least {security.MIN_PASSWORD_LENGTH} characters.")
            else:
                admin_reset_student_password(target_student_id, new_pw)
                flash(f"Password reset for student {target_student_id}.")

        elif action == "create_admin_account" and admin["role"] == "super_admin":
            new_admin_password = request.form.get("new_password", "")
            if not security.is_strong_enough_password(new_admin_password):
                flash(f"Admin password should be at least {security.MIN_PASSWORD_LENGTH} characters.")
            else:
                ok, msg = admin_auth.create_admin(
                    request.form.get("new_username", "").strip(),
                    new_admin_password,
                    request.form.get("new_role", "")
                )
                flash(msg)

        elif action == "toggle_admin_active" and admin["role"] == "super_admin":
            target_id = int(request.form.get("target_admin_id"))
            make_active = request.form.get("make_active") == "1"
            admin_auth.set_admin_active(target_id, make_active)

        return redirect(url_for("admin_portal", tab=tab))

    context = {"logged_in": True, "tab": tab, "admin": admin, "my_tabs": my_tabs}

    if tab == "notices":
        from datetime import date
        context["notices"] = portal.list_notices(include_expired=True)
        context["courses"] = course_analytics.course_names()
        context["now_date"] = date.today().isoformat()
    elif tab in ("events", "courses", "facilities"):
        kind = {"events": "event", "courses": "course", "facilities": "facility"}[tab]
        context["kind"] = kind
        context["activities"] = portal.list_activities(kind)
    elif tab == "hostel":
        context["requests"] = portal.list_all_hostel_requests()
        context["statuses"] = portal.HOSTEL_REQUEST_STATUSES
    elif tab == "grievances":
        context["grievances"] = portal.list_all_grievances()
        context["statuses"] = portal.GRIEVANCE_STATUSES
    elif tab == "academics":
        students = portal.list_all_students()
        for s in students:
            s["record"] = portal.get_academic_record(s["student_id"])
        context["students"] = students
    elif tab == "transport":
        context["routes"] = campus_info.list_routes()
    elif tab == "gallery":
        context["images"] = gallery.list_images()
        context["categories"] = gallery.CATEGORIES
    elif tab == "students":
        context["students"] = portal.list_all_students()
    elif tab == "admins":
        context["admins"] = admin_auth.list_admins()
        context["roles"] = admin_auth.ADMIN_ROLES

    return render_template("admin_portal.html", **context)


# ====================================================
# RUN
# ====================================================

if __name__ == "__main__":
    app.run(debug=True)