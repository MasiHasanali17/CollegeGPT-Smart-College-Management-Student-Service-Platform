# Project Structure — Campus Genius

A map of the codebase, organized by what was pre-existing vs. what was built.

---

## The Chatbot (pre-existing — never modified)

```
backend/
├── rag_pipeline.py       Main chatbot orchestration
├── retrieval.py          Spell correction, FAISS search, cross-encoder re-ranking
├── groq_client.py        LLM answer generation
├── cache.py               Response caching
├── logger.py               Interaction logging
└── analytics/              Structured data lookups (courses, fees, hostels, admissions...)
    ├── router.py
    ├── course.py
    ├── admission.py
    ├── fees.py
    ├── hostel.py
    ├── faculty.py
    ├── statistics.py
    ├── indexer.py
    └── loader.py

templates/chatbot.html
static/js/chatbot.js

data/
├── knowledge_base.json     University data the chatbot draws from
├── master_documents.json
└── raw/                    Original source documents

model/
├── faiss_index.bin
├── embeddings.npy
└── metadata.json
```

Every file above was verified byte-for-byte identical to the original after every
single phase of this build (diffed automatically, not just eyeballed).

---

## Everything Built On Top (organized by feature)

### Foundation — accounts & database
```
backend/database.py      All table definitions + migrations (14 tables total)
backend/auth.py          Student registration/login/password-reset logic
backend/admin_auth.py    Admin account login + role-permission checking
backend/security.py      CSRF protection, rate limiting, secret key management
```

### Public Site (no login) — "Interface 1"
```
backend/prospective.py       Admission applications, contact messages
backend/scholarship_data.py  Real scholarship data + matching logic
backend/campus_info.py       Transport routes
backend/gallery.py           Photo gallery
backend/site_search.py       Site-wide quick search
backend/uploads.py           Shared file-upload + image-optimization helper
backend/generate_brochure.py PDF brochure generator (run manually, not on every request)

templates/
├── fee_calculator.html, eligibility_checker.html, scholarship_checker.html
├── admission.html, track_application.html
├── hostel_info.html, transport.html, campus_tour.html, campus_life.html
├── gallery.html, search_results.html
├── compare.html (rebuilt with real data)
└── contact.html (form wired to actually submit)
```

### Student Portal (login required) — "Interface 2"
```
backend/portal.py          Notices, bookings, hostel/grievance requests, academics
backend/payments.py        Razorpay integration (order creation, signature verification)
backend/notifications.py   In-app notification bell

templates/
├── dashboard.html
├── portal_notices.html, portal_events.html, portal_courses.html, portal_facilities.html
├── portal_checkout.html, portal_ticket.html, portal_my_bookings.html
├── portal_hostel_transfer.html, portal_grievance.html, portal_academics.html
└── portal_notifications.html
```

### Admin System
```
backend/create_admin.py    CLI tool to create role-specific admin accounts

templates/
├── admin_login.html
├── admin_applications.html
└── admin_portal.html      Unified panel — all 11 tabs in one template
```

### Shared / Site-wide
```
templates/base.html        Navbar, toast notifications, entry gate, footer scripts
static/css/portal.css      Shared styling for all student-portal pages
static/uploads/            Gallery images + notice PDF attachments (created at runtime)
```

---

## Database Tables (14 total)

| Table | Purpose |
|---|---|
| `students` | Student accounts |
| `admin_users` | Admin accounts + roles |
| `applications` | Admission applications |
| `contact_messages` | Contact form submissions |
| `activities` | Events / extra courses / facility slots (shared schema) |
| `activity_bookings` | Student bookings against activities |
| `payment_orders` | Razorpay order/payment tracking |
| `notices` | Notice board posts |
| `hostel_transfer_requests` | Hostel transfer requests |
| `grievances` | Student complaints |
| `academic_records` | Per-student attendance/timetable/results |
| `transport_routes` | Bus routes (admin-entered) |
| `gallery_images` | Uploaded photos |
| `notifications` | Student notification bell entries |

---

## How to Trace a Feature

Every feature follows the same pattern: a `backend/*.py` file holds the database
functions, `app.py` has the routes that call them, and one or more `templates/*.html`
files render the pages. If you want to understand or modify a specific feature, start
by finding its `backend/*.py` module (they're all named after what they do), then
search `app.py` for routes calling into it.
