"""
create_admin.py

Command-line tool for creating admin accounts with a specific role.
Run from the backend/ folder:

    python create_admin.py

The very first super_admin account (username: superadmin, password:
admin123) is created automatically the first time the app runs
(see database.py, _bootstrap_super_admin) — use THIS script to create
additional role-specific accounts, e.g. a Hostel Admin or Grievance Admin
who should only see their own tab.
"""

import sys
import getpass

sys.path.insert(0, ".")

from database import init_db, ADMIN_ROLES
import admin_auth


def main():
    init_db()

    print("=== Create Admin Account ===\n")

    username = input("Username: ").strip()

    if not username:
        print("Username cannot be empty.")
        return

    print("\nAvailable roles:")
    for i, role in enumerate(ADMIN_ROLES, 1):
        print(f"  {i}. {role}")

    role_choice = input("\nRole (number or name): ").strip()

    if role_choice.isdigit() and 1 <= int(role_choice) <= len(ADMIN_ROLES):
        role = ADMIN_ROLES[int(role_choice) - 1]
    elif role_choice in ADMIN_ROLES:
        role = role_choice
    else:
        print("Invalid role choice.")
        return

    password = getpass.getpass("Password: ")
    confirm = getpass.getpass("Confirm password: ")

    if password != confirm:
        print("Passwords don't match.")
        return

    if len(password) < 6:
        print("Password should be at least 6 characters.")
        return

    success, message = admin_auth.create_admin(username, password, role)

    print(f"\n{'✓' if success else '✗'} {message}")


if __name__ == "__main__":
    main()
