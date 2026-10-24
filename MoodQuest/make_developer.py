"""Check accounts or choose the developer account.

  python make_developer.py                      -> list accounts and who is developer
  python make_developer.py you@gmail.com        -> make that account the only developer
"""
import sys

import auth

if len(sys.argv) < 2:
    users = auth.list_users()
    if not users:
        print("No accounts yet. Start the app and create one first.")
    for email, is_dev, provider in users:
        print(f"{email:35} developer={is_dev}  ({provider})")
else:
    target = sys.argv[1]
    if auth.set_developer(target):
        print(f"{target.lower()} is now the only developer account.")
    else:
        print(f"No account with email {target}. Create it in the app first. Accounts:")
        for email, is_dev, _ in auth.list_users():
            print("  ", email, "developer" if is_dev else "")
