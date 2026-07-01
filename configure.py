"""
Interactive configurator for Grandpa's MariaDB Terminal.

Prompts for the connection password (and whether to use one at all) and
writes it into config.toml using tomlkit, which preserves the file's
comments and layout instead of rewriting it from scratch.

Run directly, or let setup.bat / setup.sh call it for you:

    python configure.py
"""

import os
import getpass

import tomlkit

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(HERE, "config.toml")


def load_doc():
    """Load config.toml, or start a fresh document if it's missing."""
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
            return tomlkit.parse(fh.read())

    doc = tomlkit.document()
    doc["use_password"] = True
    doc["host"] = "127.0.0.1"
    doc["port"] = 3306
    doc["user"] = "root"
    doc["password"] = ""
    doc["charset"] = "utf8mb4"
    return doc


def ask_yes_no(prompt, default=True):
    suffix = "[Y/n]" if default else "[y/N]"
    answer = input(f"{prompt} {suffix} ").strip().lower()
    if not answer:
        return default
    return answer in ("y", "yes")


def main():
    doc = load_doc()

    print("Setting up your MariaDB connection.")
    print("(Press Enter to keep the current value shown in brackets.)\n")

    # Host / port / user are handy to confirm too, with current values as defaults.
    host = input(f"Host [{doc.get('host', '127.0.0.1')}]: ").strip()
    if host:
        doc["host"] = host

    user = input(f"User [{doc.get('user', 'root')}]: ").strip()
    if user:
        doc["user"] = user

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

    with open(CONFIG_PATH, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(tomlkit.dumps(doc))

    print(f"\nSaved to {CONFIG_PATH}")
    print("You're ready -- start the tool with run.bat (Windows) or ./run.sh.")


if __name__ == "__main__":
    main()
