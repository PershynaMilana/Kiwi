"""
Syncs data directly from PostgreSQL to Firestore using gcloudc's document ID format.
Run with: python sync_postgres_to_firestore.py
"""
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tcms.settings.devel")
django.setup()

import datetime
import psycopg2
import psycopg2.extras
from google.cloud import firestore

DB_PARAMS = {"dbname": "kiwi", "user": "kiwi", "password": "kiwi", "host": "localhost"}
FIRESTORE_PROJECT = "kiwi-tcms-d90e9"

INT_KEY_LEN = 20  # gcloudc zero-pads integer PKs to 20 chars


def pk_to_doc_id(pk):
    return str(pk).zfill(INT_KEY_LEN)


def coerce_value(v):
    if isinstance(v, datetime.timedelta):
        return int(v.total_seconds())
    return v


def sync_table(cur, fs_db, pg_table, fs_collection, pk_col="id"):
    cur.execute(f"SELECT * FROM {pg_table}")
    rows = cur.fetchall()
    count = 0
    for row in rows:
        row = {k: coerce_value(v) for k, v in dict(row).items()}
        pk = row.pop(pk_col)
        fs_db.collection(fs_collection).document(pk_to_doc_id(pk)).set(row)
        count += 1
    print(f"  {fs_collection}: {count} synced")
    return count


def get_columns(cur, pg_table):
    cur.execute(f"SELECT * FROM {pg_table} LIMIT 0")
    return [desc[0] for desc in cur.description]


conn = psycopg2.connect(**DB_PARAMS)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
fs_db = firestore.Client(project=FIRESTORE_PROJECT)

print("Syncing PostgreSQL → Firestore (gcloudc collections)...")

tables = [
    ("auth_user",                       "auth_user",                       "id"),
    ("auth_group",                      "auth_group",                      "id"),
    ("management_classification",       "management_classification",       "id"),
    ("management_product",              "management_product",              "id"),
    ("management_version",              "management_version",              "id"),
    ("management_build",                "management_build",                "id"),
    ("management_component",            "management_component",            "id"),
    ("management_tag",                  "management_tag",                  "id"),
    ("management_priority",             "management_priority",             "id"),
    ("testplans_plantype",              "testplans_plantype",              "id"),
    ("testcases_bugsystem",             "testcases_bugsystem",             "id"),
    ("testcases_testcasestatus",        "testcases_testcasestatus",        "id"),
    ("testcases_category",              "testcases_category",              "id"),
    ("testcases_template",              "testcases_template",              "id"),
    ("testcases_testcase",              "testcases_testcase",              "id"),
    ("testcases_testcaseemailsettings", "testcases_testcaseemailsettings", "id"),
    ("testruns_testexecutionstatus",    "testruns_testexecutionstatus",    "id"),
    ("testruns_environment",            "testruns_environment",            "id"),
    ("testruns_testrun",                "testruns_testrun",                "id"),
    ("testruns_testexecution",          "testruns_testexecution",          "id"),
    ("testplans_testplan",              "testplans_testplan",              "id"),
    ("testplans_testplanemailsettings", "testplans_testplanemailsettings", "id"),
    ("bugs_bug",                        "bugs_bug",                        "id"),
    ("bugs_severity",                   "bugs_severity",                   "id"),
    ("linkreference_linkreference",     "linkreference_linkreference",     "id"),
    ("auth_user_groups",                "auth_user_groups",                "id"),
    ("auth_user_user_permissions",      "auth_user_user_permissions",      "id"),
    ("auth_group_permissions",          "auth_group_permissions",          "id"),
    ("testplans_testplantag",           "testplans_testplantag",           "id"),
    ("testruns_testruntag",             "testruns_testruntag",             "id"),
    ("testruns_testruncc",              "testruns_testruncc",              "id"),
]

# Find correct column names for M2M tables dynamically
m2m_tables = [
    "testcases_testcaseplan",
    "testcases_testcasetag",
    "testcases_testcasecomponent",
]
for t in m2m_tables:
    try:
        cols = get_columns(cur, t)
        print(f"  {t} columns: {cols}")
        tables.append((t, t, cols[0]))  # assume first col is pk
    except Exception as e:
        print(f"  Could not inspect {t}: {e}")

for pg_table, fs_col, pk_col in tables:
    try:
        sync_table(cur, fs_db, pg_table, fs_col, pk_col=pk_col)
    except Exception as e:
        print(f"  ERROR {pg_table}: {e}")

cur.close()
conn.close()
print("\nDone.")
