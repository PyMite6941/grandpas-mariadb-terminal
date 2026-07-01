# Grandpa's MariaDB Terminal

> 🎂 **A birthday gift for my grandfather.** Happy birthday, Grandpa — this one's
> for you. Made with love so your database work feels a little more colorful.

A color-coded command-line client for MariaDB — a nicer alternative to the
plain `mysql` client, built with the `rich` library.

## Easiest way (one script does everything)

If you'd rather not run the steps by hand, use the included scripts — they
create a virtual environment, install the packages, and launch the tool.

**Windows** — double-click `setup.bat` once, then `run.bat` to start it.

**Linux / macOS:**

```
chmod +x setup.sh run.sh   # first time only
./setup.sh                 # installs everything
./run.sh                   # starts the tool
```

The setup script installs the packages **and** asks you for your password,
saving it base64-encoded into `config.toml` for you (using `tomlkit`, so
the file's comments stay intact) — no manual editing needed. Your password
is never stored in plaintext on disk. To change it later, just run
`python configure.py` again.

---

## Or do it manually

### 1. Install the packages

```
pip install pymysql rich
```

(or `pip install -r requirements.txt` if you keep that file alongside it)

### 2. Set your password

The connection settings live in `config.toml`. The easiest way to set the
password is to run the configurator, which writes it base64-encoded into
the file for you:

```
python configure.py
```

Your password is **never stored in plaintext** — `configure.py` encodes it
before writing to disk, and the terminal decodes it when connecting. If you
edit `config.toml` by hand, you can put a plaintext password (it works too):

```toml
use_password = true   # set to false to connect without a password
password = ""         # base64-encoded; run configure.py to set it
```

- If your server needs a password, leave `use_password = true` and set
  `password`.
- If your server has **no** password set, change it to `use_password = false`
  and you can skip the password entirely.

### 3. Run it

```
python mariadb_terminal.py
```

You'll get a `sql>` prompt. Type any SQL and hit Enter:

```
sql> SHOW DATABASES;
sql> USE some_database;
sql> SELECT * FROM some_table;
```

Shortcut commands (no semicolon needed):
- `\l` — list all databases
- `\d` — list tables in the current database
- `\dt tablename` — show a table's columns and types
- `\q` — quit

Numbers show up in yellow, missing values show as a dim `NULL`, and every
query tells you how many rows it returned and how long it took.

---

## How the code works

**`connect()`** opens the connection using `pymysql`, with
`autocommit=True` so changes (INSERT/UPDATE/DELETE) take effect right
away — same behavior as the standard `mysql` CLI.

**`print_results()`** is the core of the "cool terminal" part. After a
query runs, `cursor.description` tells you whether it was a SELECT (it's
not `None`, and has column info) or something like an INSERT (it's
`None`). For SELECTs, it builds a `rich.Table`, adds one column per
result column, then loops through every row and colors each value based
on its type — that's just three `isinstance`/`is None` checks.

**`handle_meta_command()`** intercepts anything starting with `\` before
it reaches the database, and translates it into the real SQL command
MariaDB understands (`\l` becomes `SHOW DATABASES`, etc.). This is the
same trick tools like `psql` and `mycli` use for their shortcuts.

**`Syntax(query, "sql", theme="monokai")`** re-prints your query with SQL
syntax highlighting before running it — purely cosmetic, but it's what
makes the tool feel like a real developer tool instead of a plain input
box.

**`import readline`** is the one-line trick that gives you up-arrow
history in the terminal. Python's built-in `input()` automatically
gains that behavior on Linux/Mac the moment `readline` is imported,
even though the code never calls it directly.

**The `while True` loop with `\q` to break** is a REPL (Read-Eval-Print
Loop) — the same pattern the Python interactive shell, `mysql` client,
and most database tools use under the hood.
