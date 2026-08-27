# Admin Guide — Campus Genius

How to use every part of the admin system.

---

## Logging in

Two separate admin areas, one shared login:

- `/admin/login` — log in here first
- `/admin/portal` — manage student-portal content (notices, events, hostel requests, etc.)
- `/admin/applications` — manage prospective-student admission applications

Which of these you can actually see depends on your **role** (see below).

---

## Roles & What They Can Access

| Role | Can access |
|---|---|
| **super_admin** | Everything, including creating/managing other admin accounts |
| **admission_admin** | Applications page only |
| **hostel_admin** | Hostel Requests + Transport tabs |
| **grievance_admin** | Grievances tab |
| **academic_admin** | Academics tab |
| **student_services_admin** | Notices, Events, Extra Courses, Sports/Gym, Gallery tabs |

If you try to access a section your role doesn't cover — whether by clicking a link
that shouldn't be there, or typing the URL directly — you'll be redirected with a
message. This is enforced on the server, not just hidden in the UI.

---

## Admin Portal Sections (`/admin/portal`)

### Notices
Post announcements with a category, optional expiry date, target audience, and an
optional PDF attachment. Notices past their expiry date automatically stop showing to
students (but stay visible to you here, marked "(expired)", so you can clean them up).

### Events / Extra Courses / Sports & Gym
These three tabs work identically — add a title, schedule, capacity (0 = unlimited),
and price (0 = free). Paid items go through the real Razorpay checkout on the student
side; free ones book instantly. Deleting an item also removes any bookings students
made for it (no orphaned data).

### Hostel Requests
See every transfer request submitted by students. Update the status dropdown
(Submitted → Under Review → Approved/Rejected → Completed) — the student is notified
automatically the moment you change it.

### Grievances
Same pattern as Hostel Requests — view, update status, student gets notified.

### Academics
Enter/update attendance %, exam timetable, and results per student. Since this project
doesn't have access to a real university ERP, this is admin-entered rather than
auto-synced — see the project notes for why that's the honest approach here.

### Transport
Add real bus routes (name, stops, timing, contact) as they become available. Starts
empty on purpose — no fake routes are pre-filled.

### Gallery
Upload real photos (JPG/PNG/WEBP/GIF, up to 10MB). Images are automatically resized
and compressed on upload (typically 80-90% smaller) without needing you to do anything.

### Students *(super_admin only)*
Reset any student's password directly — useful for students who forgot their security
question answer too.

### Manage Admins *(super_admin only)*
Create new admin accounts (pick username, password, role) and deactivate/reactivate
existing ones. The default `superadmin` account can't be deactivated by accident (no
button shown for it) — create yourself a new super admin account and only then
deactivate the default one if you want it gone.

---

## Applications Page (`/admin/applications`)

Separate from the portal — this manages prospective-student admission applications
submitted through the public site. Update each application's status; students can
check their own status anytime using the tracking ID they were given
(`PU-XXXXXX` format) at `/admission/track`.

---

## Security Notes

- Both student and admin logins lock out for 5 minutes after 5 failed attempts.
- Admin sessions auto-expire after 3 hours — you'll need to log in again.
- Every form is CSRF-protected.
- All admin actions are logged to the standard Flask server output (visible in your
  terminal while `app.py` is running).

## Changing the Default Password

1. Log in as `superadmin` / `admin123`
2. Go to **Manage Admins**
3. Create a new account with your own username/password and role `super_admin`
4. Log out, log back in with your new account
5. Go back to Manage Admins and deactivate `superadmin`

(There's currently no in-panel "change my own password" button — this create-new /
deactivate-old approach is the way to fully retire the default credentials. A student's
own password can always be changed via the Students tab or the student's own
forgot-password flow.)
