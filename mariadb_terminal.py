"""
Grandpa's MariaDB Terminal
==========================

A color-coded command-line client for MariaDB, built with the `rich`
library as a friendlier alternative to the plain `mysql` client.

Made with love as a birthday gift for Grandpa. Happy birthday! 🎉
"""

import sys
import time

# `readline` gives us up-arrow command history for free: Python's built-in
# input() automatically gains that behavior on Linux/Mac the moment this
# module is imported, even though we never call it directly. (It may be
# missing on plain Windows Python; that's fine, history just won't work.)
try:
    import readline  # noqa: F401
except ImportError:
    pass

import pymysql
from rich.console import Console
from rich.table import Table
from rich.syntax import Syntax

console = Console()

# ---------------------------------------------------------------------------
# Connection settings.
#
# USE_PASSWORD toggles whether we send a password at all:
#   * True  -> use the "password" value below (fill it in).
#   * False -> connect with no password (for a MariaDB set up without one).
# ---------------------------------------------------------------------------
USE_PASSWORD = True     # set to False to connect without a password

CONFIG = {
    "host": "127.0.0.1",
    "port": 3306,
    "user": "root",
    "password": "",     # fill in the password (used only when USE_PASSWORD is True)
    "charset": "utf8mb4",
}


def connect():
    """Open the connection to MariaDB.

    autocommit=True so INSERT/UPDATE/DELETE take effect right away --
    the same behavior as the standard `mysql` command-line client.

    When USE_PASSWORD is False we drop the password entirely so we can
    log in to a server that has no password set.
    """
    settings = dict(CONFIG)
    if not USE_PASSWORD:
        settings.pop("password", None)
    return pymysql.connect(autocommit=True, **settings)


def print_results(cursor, elapsed):
    """Pretty-print the result of a query.

    cursor.description is None for statements that don't return rows
    (INSERT, UPDATE, CREATE, ...). For a SELECT it holds one entry per
    column, which is how we tell the two cases apart.
    """
    if cursor.description is None:
        # Not a SELECT -- report affected rows instead.
        console.print(
            f"[green]OK[/green] -- {cursor.rowcount} row(s) affected "
            f"[dim]({elapsed * 1000:.1f} ms)[/dim]"
        )
        return

    columns = [col[0] for col in cursor.description]
    rows = cursor.fetchall()

    table = Table(show_lines=False, header_style="bold cyan")
    for name in columns:
        table.add_column(name)

    for row in rows:
        cells = []
        for value in row:
            if value is None:
                cells.append("[dim]NULL[/dim]")
            elif isinstance(value, bool):
                cells.append(f"[magenta]{value}[/magenta]")
            elif isinstance(value, (int, float)):
                cells.append(f"[yellow]{value}[/yellow]")
            else:
                cells.append(str(value))
        table.add_row(*cells)

    console.print(table)
    console.print(
        f"[dim]{len(rows)} row(s) in set ({elapsed * 1000:.1f} ms)[/dim]"
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
    console.print("[bold green]Grandpa's MariaDB Terminal[/bold green]")
    console.print("Type SQL and press Enter. [dim]\\q to quit, "
                  "\\l list databases, \\d list tables, \\dt <t> describe.[/dim]\n")

    try:
        conn = connect()
    except Exception as exc:
        console.print(f"[red]Could not connect: {exc}[/red]")
        console.print("[dim]Did you set the password in mariadb_terminal.py?[/dim]")
        sys.exit(1)

    cursor = conn.cursor()

    # A REPL (Read-Eval-Print Loop): the same pattern the Python shell,
    # the mysql client, and most database tools use under the hood.
    while True:
        try:
            line = input("sql> ").strip()
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
