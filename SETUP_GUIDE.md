# Setup Guide — Campus Genius

Full walkthrough from a fresh unzip to a running server.

---

## 1. Requirements

- Python 3.10+ recommended (project developed/tested on Python 3.12)
- pip

## 2. Install dependencies

From the project root (the folder containing `backend/`, `templates/`, `static/`):

```bash
pip install -r requirements.txt
```

This installs everything: Flask, the chatbot's ML stack (sentence-transformers, FAISS,
Groq SDK), Razorpay, QR code generation, Pillow (image optimization), PDF generation,
and gzip compression support.

> First install will take a few minutes — sentence-transformers pulls in PyTorch.

## 3. Set up environment variables

Copy the template and fill in your own key:

```bash
cp .env.example .env
```

Open `.env` and set:

```
GROQ_API_KEY=your_actual_groq_key
```

This is the only **required** value — get a free key at https://console.groq.com.

Everything else in `.env` is optional (see `.env.example` for what each one does).

## 4. Run the app

```bash
cd backend
python app.py
```

First run will:
- Download the chatbot's embedding + re-ranking models (needs internet, one-time —
  cached locally after)
- Create `data/students.db` with all tables
- Auto-create a default admin account: **`superadmin`** / **`admin123`**
- Auto-generate a session secret key, saved to `data/.secret_key`

You should see output ending in something like:

```
======================================
 Retrieval Pipeline Ready
======================================
...
[Database] students.db ready.
* Running on http://127.0.0.1:5000
```

## 5. Open the site

Go to `http://127.0.0.1:5000` in your browser.

## 6. Log into the admin panel

Go to `http://127.0.0.1:5000/admin/login`

```
Username: superadmin
Password: admin123
```

**Change this password immediately** (or create your own super admin and deactivate
this one) — see ADMIN_GUIDE.md → "Managing Admin Accounts".

## 7. (Optional) Enable real payments

Without this, event tickets marked with a price will show "Payments aren't configured
yet" — everything else (free events, courses, facilities, all other features) works
regardless.

To enable:
1. Sign up free at https://dashboard.razorpay.com
2. Settings → API Keys → Generate Test Key
3. Copy the Key ID and Key Secret into `.env`:
   ```
   RAZORPAY_KEY_ID=rzp_test_xxxxxxxxxxxx
   RAZORPAY_KEY_SECRET=xxxxxxxxxxxxxxxxxxxx
   ```
4. Restart the server

Test-mode payments use fake card numbers (Razorpay provides these in their docs) — no
real money moves.

## 8. (Optional) Create additional admin accounts

Instead of giving everyone the super admin password, create role-specific accounts:

```bash
cd backend
python create_admin.py
```

Follow the prompts to pick a username, password, and role (e.g. `hostel_admin` can only
see the Hostel Requests + Transport sections). See ADMIN_GUIDE.md for what each role
can access.

## 9. Regenerating the brochure PDF

If course/fee data changes and you want the downloadable brochure to reflect it:

```bash
cd backend
python generate_brochure.py
```

This isn't automatic (no need to regenerate a static PDF on every server start) — run
it manually whenever needed.

---

## Troubleshooting

**"ModuleNotFoundError"** — you're missing a dependency. Re-run
`pip install -r requirements.txt` from the project root.

**Chatbot is slow to start** — this is normal on first run only (downloading ML
models). Subsequent starts are fast (models are cached).

**"Payments aren't configured yet"** — expected if you haven't added Razorpay keys.
Free bookings still work fully.

**Locked out of login** — both student and admin logins lock for 5 minutes after 5
failed attempts (this is a real security feature, not a bug). Wait, or use
`python -c "import sys; sys.path.insert(0,'.'); import security; security.clear_attempts('KEY')"`
from the backend folder if you're testing locally (the key format is
`student_login:IP:studentid` or `admin_login:IP:username`).

**Want a completely fresh database** — stop the server, delete `data/students.db`, and
restart. It will be recreated empty (including a fresh default admin account).
