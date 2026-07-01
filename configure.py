"""
Interactive configurator for Grandpa's MariaDB Terminal.

Prompts for the connection details (host, user, socket, password) and
writes them into config.toml using tomlkit, which preserves the file's
comments and layout instead of rewriting it from scratch.

It then connects and, if there's no database to hook up to yet, offers
to create the bundled test database (test/testdb.sql) for you.

Run directly, or let setup.bat / setup.sh call it for you:

    python configure.py
"""

import os
import getpass
import base64

import tomlkit

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(HERE, "config.toml")
TESTDB_SQL = os.path.join(HERE, "test", "testdb.sql")
TEST_DB_NAME = "grandpas_test"


def _encode_password(pw):
    if not pw:
        return ""
    return base64.b64encode(pw.encode()).decode()


def _decode_password(pw):
    if not pw:
        return ""
    try:
        return base64.b64decode(pw.encode()).decode()
    except Exception:
        return pw


def fresh_doc():
    """A brand-new config document with default values."""
    doc = tomlkit.document()
    doc["use_password"] = True
    doc["host"] = "127.0.0.1"
    doc["port"] = 3306
    doc["user"] = "root"
    doc["password"] = ""
    doc["socket"] = ""
    doc["database"] = ""
    doc["charset"] = "utf8mb4"
    doc["max_display_rows"] = 1000
    return doc


def load_doc():
    """Load config.toml, recreating it if it's missing or corrupted."""
    if not os.path.exists(CONFIG_PATH):
        print("config.toml not found -- creating a fresh one with defaults...")
        return fresh_doc()
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
            doc = tomlkit.parse(fh.read())
        if doc.get("password"):
            doc["password"] = _decode_password(str(doc["password"]))
        return doc
    except Exception as exc:
        print(f"config.toml is corrupted ({exc}) -- recreating with defaults...")
        return fresh_doc()


def ask_yes_no(prompt, default=True):
    suffix = "[Y/n]" if default else "[y/N]"
    answer = input(f"{prompt} {suffix} ").strip().lower()
    if not answer:
        return default
    return answer in ("y", "yes")


def connect(doc, with_database=False):
    """Open a pymysql connection from the settings in `doc`.

    Mirrors the client's own connect logic. When with_database is False
    we connect to the server without selecting a database (so we can
    create one). Returns None if pymysql isn't importable.
    """
    try:
        import pymysql
    except ImportError:
        return None

    settings = {
        "user": str(doc.get("user", "root")),
        "charset": str(doc.get("charset", "utf8mb4")),
        "autocommit": True,
    }
    if doc.get("use_password", True):
        settings["password"] = str(doc.get("password", ""))

    socket_path = str(doc.get("socket", "") or "")
    if socket_path:
        settings["unix_socket"] = socket_path
    else:
        settings["host"] = str(doc.get("host", "127.0.0.1"))
        settings["port"] = int(doc.get("port", 3306))

    if with_database and doc.get("database"):
        settings["database"] = str(doc["database"])

    return pymysql.connect(**settings)


def list_databases(conn):
    with conn.cursor() as cur:
        cur.execute("SHOW DATABASES;")
        return {row[0] for row in cur.fetchall()}


def run_sql_script(conn, path):
    """Execute a multi-statement .sql file, one statement at a time."""
    with open(path, "r", encoding="utf-8") as fh:
        script = fh.read()

    # Drop comment lines, then split on ';'. The bundled script has no
    # semicolons inside string literals, so a simple split is safe here.
    cleaned = "\n".join(
        line for line in script.splitlines()
        if not line.strip().startswith("--")
    )
    statements = [s.strip() for s in cleaned.split(";") if s.strip()]

    with conn.cursor() as cur:
        for stmt in statements:
            cur.execute(stmt)


def maybe_create_database(doc):
    """Connect and, if nothing is hooked up, offer to create the test DB."""
    try:
        conn = connect(doc, with_database=False)
    except Exception as exc:
        print(f"\nCouldn't connect to the server to check databases: {exc}")
        print("Skipping database setup -- you can run configure.py again later.")
        return

    if conn is None:
        print("\n(pymysql not available here -- skipping database setup.)")
        return

    try:
        existing = list_databases(conn)
        # System schemas don't count as "a database to hook up to".
        system = {"information_schema", "performance_schema", "mysql", "sys"}
        user_dbs = existing - system
        current = str(doc.get("database", "") or "")

        if current and current in existing:
            print(f"\nUsing existing database '{current}'. All set.")
            return

        if current and current not in existing:
            print(f"\nConfigured database '{current}' doesn't exist yet.")

        if not current and user_dbs:
            print("\nDatabases available on this server:")
            for name in sorted(user_dbs):
                print(f"  - {name}")
            print("(Leave 'database' blank in config.toml to pick one with USE ...; )")

        # Offer to create the bundled test database if it's not there.
        if TEST_DB_NAME not in existing:
            if os.path.exists(TESTDB_SQL) and ask_yes_no(
                f"No database is hooked up. Create the test database "
                f"'{TEST_DB_NAME}' now?",
                default=True,
            ):
                print(f"Creating '{TEST_DB_NAME}' from {os.path.relpath(TESTDB_SQL, HERE)} ...")
                run_sql_script(conn, TESTDB_SQL)
                doc["database"] = TEST_DB_NAME
                print(f"Created and hooked up '{TEST_DB_NAME}'.")
        else:
            if not current and ask_yes_no(
                f"Test database '{TEST_DB_NAME}' already exists. Hook up to it?",
                default=True,
            ):
                doc["database"] = TEST_DB_NAME
    finally:
        conn.close()


def main():
    doc = load_doc()

    print("Setting up your MariaDB connection.")
    print("(Press Enter to keep the current value shown in brackets.)\n")

    host = input(f"Host [{doc.get('host', '127.0.0.1')}]: ").strip()
    if host:
        doc["host"] = host

    user = input(f"User [{doc.get('user', 'root')}]: ").strip()
    if user:
        doc["user"] = user

    # Optional unix socket file path. Blank keeps TCP host/port.
    current_socket = doc.get("socket", "") or "(none, use TCP)"
    socket = input(
        f"MariaDB socket file path, or blank for TCP [{current_socket}]: "
    ).strip()
    if socket:
        doc["socket"] = socket

    # Password toggle + value.
    use_password = ask_yes_no(
        "Does this server need a password?",
        default=bool(doc.get("use_password", True)),
    )
    doc["use_password"] = use_password

    if use_password:
        # getpass hides typing; falls back gracefully if the terminal can't hide it.
        pw = getpass.getpass("Password (leave blank to keep current): ")
        if pw:
            doc["password"] = pw
    else:
        print("Skipping password -- connecting without one.")

    # Connect and, if needed, create/hook up a database.
    maybe_create_database(doc)

    if doc.get("password"):
        doc["password"] = _encode_password(str(doc["password"]))

    with open(CONFIG_PATH, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(tomlkit.dumps(doc))

    print(f"\nSaved to {CONFIG_PATH}")
    print("You're ready -- start the tool with run.bat (Windows) or ./run.sh.")


if __name__ == "__main__":
    main()
