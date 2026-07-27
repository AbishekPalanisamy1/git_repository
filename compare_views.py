import os
import re
import difflib
import mysql.connector
import requests

# =====================================================
# CONFIGURATION
# =====================================================

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "Canny@1234",
    "database": "company"
}

# GitHub repo containing the SQL files
GITHUB_CONFIG = {
    "owner": "AbishekPalanisamy1",
    "repo": "git_repository",
    "branch": "main",
    "path": "sql_views/Views",   # folder inside the repo that holds the .sql files

    # Optional: a Personal Access Token. Required for private repos,
    # and recommended even for public repos to avoid GitHub's low
    # unauthenticated rate limit (60 requests/hour vs 5000/hour with a token).
    # Create one at https://github.com/settings/tokens (repo:read scope is enough).
    "token": None
}

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

    views = [row[0] for row in cur.fetchall()]

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
        return row[1]

    return None


def get_git_view_definition(view_name, git_sql):
    """
    Create a temporary view from the Git SQL so MySQL canonicalizes it
    the exact same way it canonicalizes the real view (adds column
    aliases, wraps joins in parentheses, etc). Then fetch SHOW CREATE VIEW
    for that temp view and drop it.
    """

    temp_name = view_name + "_gitcheck_tmp"

    # Replace the view name in the git SQL with the temp name so we don't
    # clobber the real view. Handles CREATE VIEW / CREATE OR REPLACE VIEW,
    # with or without backticks around the name.
    temp_sql, n = re.subn(
        r'(create\s+(or\s+replace\s+)?view\s+)`?' + re.escape(view_name) + r'`?',
        r'\1`' + temp_name + '`',
        git_sql,
        count=1,
        flags=re.I
    )

    if n == 0:
        raise ValueError(
            f"Could not find 'CREATE VIEW {view_name}' in the git SQL file "
            f"to rename it for comparison."
        )

    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute(f"DROP VIEW IF EXISTS `{temp_name}`")
        cur.execute(temp_sql)
        cur.execute(f"SHOW CREATE VIEW `{temp_name}`")
        row = cur.fetchone()
        cur.execute(f"DROP VIEW IF EXISTS `{temp_name}`")
        conn.commit()
        return row[1] if row else None

    except Exception:
        try:
            cur.execute(f"DROP VIEW IF EXISTS `{temp_name}`")
            conn.commit()
        except Exception:
            pass
        raise

    finally:
        cur.close()
        conn.close()


# =====================================================
# READ SQL FILES FROM GITHUB
# =====================================================

_github_file_list_cache = None  # populated once per run


def _github_headers():
    headers = {"Accept": "application/vnd.github+json"}

    if GITHUB_CONFIG.get("token"):
        headers["Authorization"] = f"token {GITHUB_CONFIG['token']}"

    return headers


def _list_github_sql_files():
    """
    Calls the GitHub Contents API once and caches the result for this run.
    Returns a dict of { "view_name" (lowercase, no .sql) : download_url }
    """

    global _github_file_list_cache

    if _github_file_list_cache is not None:
        return _github_file_list_cache

    url = (
        f"https://api.github.com/repos/"
        f"{GITHUB_CONFIG['owner']}/{GITHUB_CONFIG['repo']}/contents/"
        f"{GITHUB_CONFIG['path']}"
    )

    resp = requests.get(
        url,
        headers=_github_headers(),
        params={"ref": GITHUB_CONFIG["branch"]},
        timeout=30
    )

    if resp.status_code != 200:
        raise RuntimeError(
            f"GitHub API request failed ({resp.status_code}): {resp.text[:300]}"
        )

    items = resp.json()

    files = {}

    for item in items:

        if item.get("type") != "file":
            continue

        name = item.get("name", "")

        if not name.lower().endswith(".sql"):
            continue

        view_name = name[:-4]  # strip ".sql"
        files[view_name.lower()] = {
            "actual_name": view_name,
            "download_url": item["download_url"]
        }

    _github_file_list_cache = files
    return files


def read_sql_file(view_name):
    """Fetch the raw .sql file content for a view from GitHub (case-insensitive match)."""

    files = _list_github_sql_files()
    entry = files.get(view_name.lower())

    if entry is None:
        return None

    resp = requests.get(entry["download_url"], headers=_github_headers(), timeout=30)

    if resp.status_code != 200:
        raise RuntimeError(
            f"Failed to download '{entry['actual_name']}.sql' from GitHub "
            f"({resp.status_code}): {resp.text[:300]}"
        )

    return resp.text


def get_all_git_view_names():
    """Return the set of view names found in the GitHub folder,
    based on .sql filenames (case-insensitive, matches MySQL view
    name comparison behaviour on most default configs)."""

    files = _list_github_sql_files()
    return {entry["actual_name"] for entry in files.values()}


# =====================================================
# NORMALIZE SQL
# =====================================================

def normalize(sql):

    if sql is None:
        return ""

    # lowercase
    sql = sql.lower()

    # remove comments
    sql = re.sub(r'--.*', '', sql)
    sql = re.sub(r'/\*.*?\*/', '', sql, flags=re.S)

    # remove mysql specific options
    sql = re.sub(r'algorithm\s*=\s*\w+', '', sql)
    sql = re.sub(r"definer\s*=\s*`[^`]*`@`[^`]*`", '', sql)
    sql = re.sub(r'sql security\s+\w+', '', sql)

    # remove backticks
    sql = sql.replace("`", "")

    # remove the view name itself so real-vs-temp naming differences
    # (e.g. vw_x vs vw_x_gitcheck_tmp) don't cause false mismatches
    sql = re.sub(r'(create\s+(or\s+replace\s+)?view\s+)\S+', r'\1<VIEW>', sql, count=1)

    cleaned_lines = []

    for line in sql.splitlines():

        line = line.strip()

        if line == "":
            continue

        line = re.sub(r'\s+', ' ', line)

        cleaned_lines.append(line)

    return "\n".join(cleaned_lines).strip().rstrip(";")


# =====================================================
# PRETTY-PRINT FOR DIFF DISPLAY
# =====================================================

# Clause keywords that should each start on their own line
_CLAUSE_KEYWORDS = [
    "create or replace view", "create view",
    "left outer join", "right outer join",
    "left join", "right join", "inner join", "join",
    "select", "from", "on", "where",
    "group by", "order by", "having", "union all", "union"
]


def _split_top_level_commas(s):
    """Split on commas that are NOT inside parentheses,
    e.g. splits 'a, count(b, c), d' into ['a', 'count(b, c)', 'd']."""

    parts = []
    depth = 0
    current = ""

    for ch in s:

        if ch == "(":
            depth += 1
            current += ch

        elif ch == ")":
            depth -= 1
            current += ch

        elif ch == "," and depth == 0:
            parts.append(current.strip())
            current = ""

        else:
            current += ch

    if current.strip():
        parts.append(current.strip())

    return parts


def to_diff_lines(normalized_sql):
    """
    Take a normalized (single-line, lowercase) SQL string and break it
    into one line per clause keyword and one line per top-level column/
    expression, purely for readable diffing. Does NOT change the
    match/mismatch decision -- that still uses the raw normalized string.
    """

    text = normalized_sql

    # Insert a marker before each clause keyword (longest first so
    # e.g. "left join" is matched before "join")
    for kw in sorted(_CLAUSE_KEYWORDS, key=len, reverse=True):
        text = re.sub(r'(?<!\S)' + re.escape(kw) + r'(?!\S)',
                       '\n' + kw.upper() + ' ', text)
        # also catch keyword when followed immediately by non-space (rare)
        text = re.sub(r'\b' + re.escape(kw) + r'\b',
                       lambda m: m.group(0), text)

    lines = []

    for chunk in text.split("\n"):

        chunk = chunk.strip()

        if not chunk:
            continue

        # Split the clause header (e.g. "SELECT") from its body
        matched_kw = None
        for kw in sorted(_CLAUSE_KEYWORDS, key=len, reverse=True):
            if chunk.upper().startswith(kw.upper()):
                matched_kw = kw
                break

        if matched_kw:
            header = chunk[:len(matched_kw)]
            body = chunk[len(matched_kw):].strip()
        else:
            header = None
            body = chunk

        if not body:
            if header:
                lines.append(header.upper())
            continue

        # For select-lists / group-by lists, split on top-level commas
        for piece in _split_top_level_commas(body):
            if header:
                lines.append(f"{header.upper()} {piece}".strip())
                header = None  # only prefix the first piece
            else:
                lines.append(piece)

    return lines


# =====================================================
# COMPARE
# =====================================================

def compare(view_name):

    db_sql_raw = get_view_definition(view_name)
    git_sql_raw = read_sql_file(view_name)

    print("\n" + "=" * 100)
    print("VIEW :", view_name)
    print("=" * 100)

    if git_sql_raw is None:
        print("STATUS : FILE NOT FOUND IN GIT")
        return "missing"

    # Run the git SQL through MySQL as a temp view so it gets canonicalized
    # the same way the real view was, making the comparison apples-to-apples.
    git_sql_canonical = get_git_view_definition(view_name, git_sql_raw)

    db_sql = normalize(db_sql_raw)
    git_sql = normalize(git_sql_canonical)

    if db_sql == git_sql:
        print("STATUS : MATCH")
        return "match"

    print("STATUS : DIFFERENT")
    print("-" * 100)

    db_lines = to_diff_lines(db_sql)
    git_lines = to_diff_lines(git_sql)

    diff = difflib.ndiff(db_lines, git_lines)

    for line in diff:

        if line.startswith("- "):
            print("DATABASE :", line[2:])

        elif line.startswith("+ "):
            print("GIT      :", line[2:])

    print("-" * 100)

    return "different"


# =====================================================
# MAIN
# =====================================================

def main():

    try:
        _list_github_sql_files()  # verifies GitHub repo/path is reachable

    except Exception as ex:

        print("Could not reach GitHub SQL folder")
        print(
            f"Repo: {GITHUB_CONFIG['owner']}/{GITHUB_CONFIG['repo']} "
            f"Branch: {GITHUB_CONFIG['branch']} Path: {GITHUB_CONFIG['path']}"
        )
        print(ex)
        return

    try:
        views = get_all_views()

    except Exception as ex:

        print("Database connection failed")
        print(ex)
        return

    matched = 0
    different = 0
    missing = 0
    errors = 0

    print("\nFound", len(views), "views in database.\n")

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

            print("ERROR :", view)
            print(ex)

    # -------------------------------------------------
    # Cross-check: views that exist in Git but NOT in DB
    # -------------------------------------------------

    db_view_names_lower = {v.lower() for v in views}
    git_view_names = get_all_git_view_names()

    only_in_git = sorted(
        name for name in git_view_names
        if name.lower() not in db_view_names_lower
    )

    if only_in_git:

        print("\n")
        print("=" * 100)
        print("VIEWS FOUND IN GIT BUT NOT IN DATABASE")
        print("=" * 100)

        for name in only_in_git:
            print(" -", name)

    print("\n")
    print("=" * 100)
    print("SUMMARY")
    print("=" * 100)
    print(f"Total Views in DB      : {len(views)}")
    print(f"Matched                : {matched}")
    print(f"Different              : {different}")
    print(f"In DB but not in Git   : {missing}")
    print(f"In Git but not in DB   : {len(only_in_git)}")
    print(f"Errors                 : {errors}")
    print("=" * 100)


if __name__ == "__main__":
    main()