"""Generates messy sample data: CSV (CRM), SQLite (legacy billing), JSON Lines (orders)."""
import csv
import json
import os
import random
import sqlite3
import sys
from datetime import date, timedelta

N_CUSTOMERS = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
N_ORDERS = int(sys.argv[2]) if len(sys.argv) > 2 else 20000
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "sample")
os.makedirs(OUT, exist_ok=True)
random.seed(42)

FIRST = ["amit", "priya", "john", "sara", "li", "omar", "anna", "ravi", "maria", "chen"]
LAST = ["sharma", "smith", "khan", "garcia", "wang", "reddy", "brown", "ali", "kumar", "lee"]
COUNTRIES = ["india", "usa", "uk", "germany", "japan", "brazil"]
DATE_FMTS = ["%Y-%m-%d", "%d/%m/%Y", "%d %b %Y"]


def rand_date():
    d = date(2020, 1, 1) + timedelta(days=random.randint(0, 2200))
    return d.strftime(random.choice(DATE_FMTS))


emails = []
for i in range(N_CUSTOMERS):
    f, l = random.choice(FIRST), random.choice(LAST)
    emails.append((f"{f}.{l}{i}@example.com", f"{f} {l}"))

# CRM CSV (with some bad rows)
with open(os.path.join(OUT, "crm_customers.csv"), "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["Email", "Name", "Country", "Signup"])
    for email, name in emails:
        if random.random() < 0.02:
            email = email.replace("@", "")        # invalid email
        w.writerow([email.upper() if random.random() < .1 else email, name, random.choice(COUNTRIES), rand_date()])

# Legacy SQLite: overlaps ~40% with CRM + some brand-new clients
db = os.path.join(OUT, "legacy.db")
if os.path.exists(db):
    os.remove(db)
conn = sqlite3.connect(db)
conn.execute("CREATE TABLE clients (client_email TEXT, client_name TEXT, nation TEXT, created TEXT)")
rows = [(e, n, random.choice(COUNTRIES), rand_date()) for e, n in random.sample(emails, int(N_CUSTOMERS * .4))]
rows += [(f"new{i}@legacy.com", f"legacy user {i}", random.choice(COUNTRIES), rand_date()) for i in range(N_CUSTOMERS // 10)]
conn.executemany("INSERT INTO clients VALUES (?,?,?,?)", rows)
conn.commit()
conn.close()

# Orders JSON Lines
with open(os.path.join(OUT, "orders.jsonl"), "w", encoding="utf-8") as fh:
    for i in range(N_ORDERS):
        rec = {"id": f"ORD-{i:07d}", "customer": random.choice(emails)[0],
               "total": f"{random.uniform(5, 900):.2f}", "qty": random.randint(1, 6), "date": rand_date()}
        if random.random() < 0.01:
            rec["total"] = "-10"                  # violates min=0
        if random.random() < 0.01:
            rec["date"] = "not-a-date"
        fh.write(json.dumps(rec) + "\n")

print(f"Generated {N_CUSTOMERS} CRM customers, {len(rows)} legacy clients, {N_ORDERS} orders in {OUT}")
