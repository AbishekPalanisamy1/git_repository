
import os
import re
import difflib
import mysql.connector

# =====================================================
# CONFIGURATION
# =====================================================

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "Canny@1234",
    "database": "company"
}

# Folder containing .sql files from your Git repository
SQL_FOLDER = r"C:\GitRepo\Database\Views"

# =====================================================
# DATABASE
# =====================================================

def get_connection():
    return mysql.connector.connect(**DB_CONFIG)

def get_all_views():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT TABLE_NAME
        FROM information_schema.VIEWS
        WHERE TABLE_SCHEMA=%s
        ORDER BY TABLE_NAME
    """, (DB_CONFIG["database"],))
    views = [r[0] for r in cur.fetchall()]
    cur.close()
    conn.close()
    return views

def get_view_definition(view_name):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"SHOW CREATE VIEW `{view_name}`")
    row = cur.fetchone()
    cur.close()
    conn.close()

    if row:
        # SHOW CREATE VIEW -> (view_name, create_sql, ...)
        return row[1]
    return None

# =====================================================
# FILE
# =====================================================

def read_sql_file(view_name):
    path = os.path.join(SQL_FOLDER, view_name + ".sql")
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

# =====================================================
# NORMALIZE SQL
# =====================================================

def normalize(sql):
    if not sql:
        return ""

    sql = sql.lower()

    # remove comments
    sql = re.sub(r'--.*', '', sql)
    sql = re.sub(r'/\*.*?\*/', '', sql, flags=re.S)

    # remove mysql specific options
    sql = re.sub(r'algorithm\s*=\s*\w+', '', sql)
    sql = re.sub(r'definer\s*=\s*`?.*?`?@`?.*?`?', '', sql)
    sql = re.sub(r'sql security\s+\w+', '', sql)

    sql = sql.replace("`", "")

    sql = re.sub(r'\s+', ' ', sql)

    return sql.strip().rstrip(";")

# =====================================================
# COMPARE
# =====================================================

def compare(view_name):

    db_sql = get_view_definition(view_name)
    file_sql = read_sql_file(view_name)

    print("=" * 80)
    print("VIEW :", view_name)
    print("=" * 80)

    if file_sql is None:
        print("STATUS : FILE NOT FOUND")
        return "missing"

    db_sql = normalize(db_sql)
    file_sql = normalize(file_sql)

    if db_sql == file_sql:
        print("STATUS : MATCH\n")
        return "match"

    print("STATUS : DIFFERENT\n")

    diff = difflib.unified_diff(
        db_sql.split(),
        file_sql.split(),
        fromfile="Database",
        tofile="Git",
        lineterm=""
    )

    for line in diff:
        print(line)

    print()
    return "different"

# =====================================================
# MAIN
# =====================================================

def main():

    if not os.path.exists(SQL_FOLDER):
        print("SQL folder not found:", SQL_FOLDER)
        return

    try:
        views = get_all_views()
    except Exception as e:
        print("Database connection failed.")
        print(e)
        return

    matched = 0
    different = 0
    missing = 0
    errors = 0

    for view in views:
        try:
            result = compare(view)

            if result == "match":
                matched += 1
            elif result == "different":
                different += 1
            elif result == "missing":
                missing += 1

        except Exception as ex:
            errors += 1
            print(f"ERROR processing {view}: {ex}")

    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print("Total Views   :", len(views))
    print("Matched       :", matched)
    print("Different     :", different)
    print("Missing Files :", missing)
    print("Errors        :", errors)
    print("=" * 80)

if __name__ == "__main__":
    main()
