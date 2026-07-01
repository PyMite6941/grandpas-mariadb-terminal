"""
Grandpa's MariaDB Terminal
==========================

A color-coded command-line client for MariaDB, built with the `rich`
library as a friendlier alternative to the plain `mysql` client.

Made with love as a birthday gift for Grandpa. Happy birthday! 🎉
"""

import os
import sys
import time
import base64

# Make stdin/stdout speak UTF-8 so non-ASCII SQL and pasted text work
# everywhere -- Windows consoles otherwise default to a legacy code page,
# which mangles Unicode and turns a UTF-8 BOM into stray characters.
for _stream in (sys.stdin, sys.stdout):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

# `readline` gives us up-arrow command history for free: Python's built-in
# input() automatically gains that behavior on Linux/Mac the moment this
# module is imported, even though we never call it directly. (It may be
# missing on plain Windows Python; that's fine, history just won't work.)
try:
    import readline  # noqa: F401
except ImportError:
    pass

import datetime
from decimal import Decimal

import pymysql
import tomlkit
from rich.console import Console
from rich.table import Table
from rich.syntax import Syntax
from rich.text import Text
from rich import box

console = Console()

# ---------------------------------------------------------------------------
# Connection settings live in config.toml (next to this file).
#
# Edit it by hand, or run `python configure.py` to fill in the password.
# The "use_password" key toggles whether a password is sent at all.
# ---------------------------------------------------------------------------
HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(HERE, "config.toml")

# Defaults used if a key is missing from config.toml.
# "socket" is the file path to the MariaDB unix socket -- leave it blank to
# connect over TCP with host/port instead.
DEFAULTS = {
    "use_password": True,
    "host": "127.0.0.1",
    "port": 3306,
    "user": "root",
    "password": "",
    "socket": "",
    "database": "",
    "charset": "utf8mb4",
    # Cap how many rows are drawn in the table so a huge SELECT stays snappy.
    # 0 means "show them all" (can be slow for very large results).
    "max_display_rows": 1000,
}

# How many rows print_results will draw; set from config in main().
MAX_DISPLAY_ROWS = 1000

# The template written whenever config.toml is missing or corrupted.
DEFAULT_CONFIG_TEXT = """\
# Grandpa's MariaDB Terminal -- connection settings
#
# You can edit this file by hand, or run:  python configure.py

# use_password toggles whether a password is sent at all:
#   true  -> use the "password" value below
#   false -> connect with no password (server set up without one)
use_password = true

host = "127.0.0.1"
port = 3306
user = "root"
password = ""        # base64-encoded (configure.py handles this; see README)
database = ""        # database to open on connect; blank = none (use USE ...; later)

# socket = file path to the MariaDB unix socket. Leave it blank to connect
# over TCP using host/port above. If you fill it in, it's used instead.
socket = ""

charset = "utf8mb4"

# max_display_rows caps how many rows are drawn per result (0 = show all).
max_display_rows = 1000

# update_level: how big a GitHub change must be before update.py prompts you.
#   "patch" = every update, "minor" = minor+major only, "major" = major only.
update_level = "patch"
"""


# Passwords written by configure.py are tagged with this prefix so we can
# tell an encoded value apart from a plaintext one with certainty.
B64_PREFIX = "b64:"


def decode_password(pw):
    """Return the usable plaintext password.

    A value tagged "b64:" was written by configure.py and is base64; a
    value without the tag is used exactly as typed (plaintext is fine).
    """
    if not isinstance(pw, str) or not pw:
        return ""
    if pw.startswith(B64_PREFIX):
        try:
            return base64.b64decode(pw[len(B64_PREFIX):].encode()).decode()
        except Exception:
            return ""  # tag present but unreadable -> treat as no password
    return pw


def write_default_config():
    """Write a fresh config.toml from the template."""
    with open(CONFIG_PATH, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(DEFAULT_CONFIG_TEXT)


def load_config():
    """Read config.toml and return a plain settings dict.

    If the file is missing or corrupted it is (re)created from the
    template so the program can always start -- with a clear message
    so you know it happened.
    """
    if not os.path.exists(CONFIG_PATH):
        console.print(
            "[yellow]config.toml not found -- creating a fresh one "
            "with default settings...[/yellow]"
        )
        write_default_config()

    settings = dict(DEFAULTS)
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
            data = tomlkit.parse(fh.read())
    except Exception as exc:
        console.print(
            f"[red]config.toml is corrupted ({exc}) -- recreating it "
            f"with default settings...[/red]"
        )
        write_default_config()
        with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
            data = tomlkit.parse(fh.read())

    for key in DEFAULTS:
        if key in data:
            # unwrap tomlkit items into plain Python values
            settings[key] = data[key].unwrap() if hasattr(data[key], "unwrap") else data[key]

    # Decode the password. configure.py tags encoded values with a "b64:"
    # prefix, so there is never any ambiguity with a hand-typed plaintext
    # password (which is used exactly as written).
    settings["password"] = decode_password(settings.get("password", ""))

    # Coerce types that pymysql is picky about, in case they were hand-edited.
    try:
        settings["port"] = int(settings.get("port", 3306))
    except (TypeError, ValueError):
        settings["port"] = 3306

    return settings


def connect():
    """Open the connection to MariaDB.

    autocommit=True so INSERT/UPDATE/DELETE take effect right away --
    the same behavior as the standard `mysql` command-line client.

    When use_password is false we drop the password entirely so we can
    log in to a server that has no password set. When a socket file path
    is given we hand it to pymysql as unix_socket and skip host/port.
    """
    settings = load_config()
    use_password = bool(settings.pop("use_password", True))
    if not use_password:
        settings.pop("password", None)

    # Display-only setting -- not a pymysql connection argument.
    settings.pop("max_display_rows", None)

    socket_path = settings.pop("socket", "")
    if socket_path:
        # A unix socket path was given -- use it instead of TCP host/port.
        settings.pop("host", None)
        settings.pop("port", None)
        settings["unix_socket"] = socket_path

    # An empty database means "connect without selecting one".
    if not settings.get("database"):
        settings.pop("database", None)

    return pymysql.connect(autocommit=True, **settings)


def format_cell(value):
    """Turn one result value into a color-coded rich Text object.

    Returning a Text (with a style) instead of a markup string keeps this
    fast on big result sets -- rich never has to re-parse markup -- and is
    injection-safe: a value containing "[red]" is treated as literal text.
    """
    if value is None:
        return Text("NULL", style="dim italic")
    # bool must come before int -- in Python True/False are ints.
    if isinstance(value, bool):
        return Text(str(value), style="bright_green" if value else "bright_red")
    if isinstance(value, (int, float, Decimal)):
        return Text(str(value), style="yellow")
    if isinstance(value, (datetime.datetime, datetime.date,
                          datetime.time, datetime.timedelta)):
        return Text(str(value), style="cyan")
    if isinstance(value, (bytes, bytearray)):
        # Binary/BLOB -- show a short hint rather than raw bytes.
        return Text(f"<{len(value)} bytes>", style="blue")
    text = str(value)
    if text == "":
        return Text("''", style="dim italic")
    return Text(text, style="green")


def print_results(cursor, elapsed):
    """Pretty-print the result of a query.

    cursor.description is None for statements that don't return rows
    (INSERT, UPDATE, CREATE, ...). For a SELECT it holds one entry per
    column, which is how we tell the two cases apart.
    """
    if cursor.description is None:
        # Not a SELECT -- report affected rows instead.
        console.print(
            f"[bold green]OK[/bold green] -- "
            f"[yellow]{cursor.rowcount}[/yellow] row(s) affected "
            f"[dim]({elapsed * 1000:.1f} ms)[/dim]"
        )
        return

    columns = [col[0] for col in cursor.description]
    rows = cursor.fetchall()
    total = len(rows)

    # Only draw up to the cap -- rendering tens of thousands of rows through
    # a styled table is slow, so we show the first chunk and say how many
    # more there are. MAX_DISPLAY_ROWS = 0 means "draw everything".
    shown = rows
    if MAX_DISPLAY_ROWS and total > MAX_DISPLAY_ROWS:
        shown = rows[:MAX_DISPLAY_ROWS]

    table = Table(
        box=box.ROUNDED,
        border_style="bright_blue",
        header_style="bold cyan",
        row_styles=["", "on grey11"],   # subtle zebra striping
    )
    for name in columns:
        # Text() keeps the header literal (no markup interpretation).
        table.add_column(Text(str(name), style="bold cyan"))

    for row in shown:
        table.add_row(*[format_cell(value) for value in row])

    console.print(table)

    if len(shown) < total:
        console.print(
            f"[yellow]Showing first {len(shown)} of {total} rows[/yellow] "
            f"[dim](raise max_display_rows in config.toml to see more)[/dim]"
        )
    console.print(
        f"[bold green]{total}[/bold green] row(s) in set "
        f"[dim]({elapsed * 1000:.1f} ms)[/dim]"
    )


def handle_meta_command(command):
    """Translate backslash shortcuts into real SQL.

    Intercepts anything starting with '\\' before it reaches the
    database -- the same trick psql and mycli use for their shortcuts.
    Returns the SQL string to run, or None if there's nothing to run.
    """
    parts = command.strip().split()
    name = parts[0]

    if name == "\\l":
        return "SHOW DATABASES;"
    if name == "\\d":
        return "SHOW TABLES;"
    if name == "\\dt":
        if len(parts) < 2:
            console.print("[red]Usage: \\dt tablename[/red]")
            return None
        return f"DESCRIBE {parts[1]};"

    console.print(f"[red]Unknown command: {name}[/red]")
    return None


def run_query(cursor, query):
    """Highlight, run, and print the results of a single SQL statement."""
    console.print(Syntax(query, "sql", theme="monokai"))
    start = time.perf_counter()
    cursor.execute(query)
    elapsed = time.perf_counter() - start
    print_results(cursor, elapsed)


def main():
    global MAX_DISPLAY_ROWS
    console.print("[bold green]Grandpa's MariaDB Terminal[/bold green]")
    console.print("Type SQL and press Enter. [dim]\\q to quit, "
                  "\\l list databases, \\d list tables, \\dt <t> describe.[/dim]\n")

    # Pick up the display cap from config (falls back to the default).
    try:
        MAX_DISPLAY_ROWS = int(load_config().get("max_display_rows", MAX_DISPLAY_ROWS))
    except (TypeError, ValueError):
        pass

    try:
        conn = connect()
    except Exception as exc:
        console.print(f"[red]Could not connect: {exc}[/red]")
        console.print("[dim]Did you set the password? Run: python configure.py[/dim]")
        sys.exit(1)

    cursor = conn.cursor()

    # A REPL (Read-Eval-Print Loop): the same pattern the Python shell,
    # the mysql client, and most database tools use under the hood.
    while True:
        try:
            # Strip a stray BOM (U+FEFF) that can sneak in from pasted or
            # piped input, then trim whitespace.
            line = input("sql> ").replace("﻿", "").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Bye![/dim]")
            break

        if not line:
            continue

        if line in ("\\q", "quit", "exit"):
            console.print("[dim]Bye![/dim]")
            break

        try:
            if line.startswith("\\"):
                query = handle_meta_command(line)
                if query is None:
                    continue
            else:
                query = line

            run_query(cursor, query)
        except Exception as exc:
            console.print(f"[red]Error: {exc}[/red]")

    cursor.close()
    conn.close()


if __name__ == "__main__":
    main()
