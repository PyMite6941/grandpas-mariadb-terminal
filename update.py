"""
Update checker for Grandpa's MariaDB Terminal.

Compares the local VERSION with the latest one on GitHub and, when the
change is big enough, offers to pull the update. You choose *how big* a
change has to be before it bothers you:

    update_level = "patch"   -> tell me about every update (x.y.Z)
    update_level = "minor"   -> only minor or bigger  (x.Y.0 and up)
    update_level = "major"   -> only major releases    (X.0.0)

Set it in config.toml (update_level = "minor"), or pass it on the command
line:  python update.py --level minor   (also: --check to only check,
--yes to update without asking).

Only the Python standard library is used, so this runs even if the
project's packages aren't installed.
"""

import os
import sys
import subprocess
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
VERSION_FILE = os.path.join(HERE, "VERSION")
CONFIG_PATH = os.path.join(HERE, "config.toml")

# Where to look for the latest VERSION file on GitHub.
OWNER = "PyMite6941"
REPO = "grandpas-mariadb-terminal"
BRANCH = "master"
REMOTE_VERSION_URL = (
    f"https://raw.githubusercontent.com/{OWNER}/{REPO}/{BRANCH}/VERSION"
)

LEVELS = {"patch": 1, "minor": 2, "major": 3}
DEFAULT_LEVEL = "patch"


def parse_version(text):
    """Turn '1.2.3' (or 'v1.2.3', '1.2') into a (major, minor, patch) tuple."""
    text = (text or "").strip().lstrip("vV")
    # Drop any pre-release/build suffix like 1.2.3-beta.
    for sep in ("-", "+", " "):
        if sep in text:
            text = text.split(sep, 1)[0]
    parts = text.split(".")
    nums = []
    for i in range(3):
        try:
            nums.append(int(parts[i]))
        except (IndexError, ValueError):
            nums.append(0)
    return tuple(nums)


def change_level(local, remote):
    """Return 'major' / 'minor' / 'patch' for the difference, or None if same/older."""
    if remote <= local:
        return None
    if remote[0] != local[0]:
        return "major"
    if remote[1] != local[1]:
        return "minor"
    return "patch"


def read_local_version():
    try:
        with open(VERSION_FILE, "r", encoding="utf-8") as fh:
            return fh.read().strip()
    except FileNotFoundError:
        return "0.0.0"


def read_remote_version(timeout=10):
    req = urllib.request.Request(
        REMOTE_VERSION_URL, headers={"User-Agent": "grandpas-mariadb-terminal"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8").strip()


def read_config_level():
    """Read update_level from config.toml if present (stdlib parser)."""
    if not os.path.exists(CONFIG_PATH):
        return None
    try:
        try:
            import tomllib  # Python 3.11+
            with open(CONFIG_PATH, "rb") as fh:
                data = tomllib.load(fh)
        except ModuleNotFoundError:
            import tomlkit
            with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
                data = tomlkit.parse(fh.read())
        level = str(data.get("update_level", "")).lower().strip()
        return level if level in LEVELS else None
    except Exception:
        return None


def ask_yes_no(prompt, default=True):
    suffix = "[Y/n]" if default else "[y/N]"
    try:
        answer = input(f"{prompt} {suffix} ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return False
    if not answer:
        return default
    return answer in ("y", "yes")


def do_update():
    """Pull the update. Uses git if this is a clone; otherwise explains how."""
    if os.path.isdir(os.path.join(HERE, ".git")):
        print("Updating with git...")
        try:
            subprocess.run(["git", "-C", HERE, "pull", "--ff-only"], check=True)
            print("Updated! Restart the tool to use the new version.")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError) as exc:
            print(f"git update failed ({exc}).")
            print("You can update manually with:  git pull")
            return False
    else:
        print("This folder isn't a git clone, so I can't auto-update it.")
        print("Download the latest version here:")
        print(f"  https://github.com/{OWNER}/{REPO}/archive/refs/heads/{BRANCH}.zip")
        return False


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    check_only = "--check" in argv
    assume_yes = "--yes" in argv or "-y" in argv

    # Threshold: CLI --level wins, else config.toml, else default.
    level = None
    if "--level" in argv:
        i = argv.index("--level")
        if i + 1 < len(argv):
            level = argv[i + 1].lower().strip()
    if level not in LEVELS:
        level = read_config_level() or DEFAULT_LEVEL

    local_text = read_local_version()
    local = parse_version(local_text)
    print(f"Grandpa's MariaDB Terminal -- current version {local_text}")

    try:
        remote_text = read_remote_version()
    except Exception as exc:
        print(f"Couldn't check GitHub for updates ({exc}).")
        print("Check your internet connection and try again later.")
        return 1

    remote = parse_version(remote_text)
    change = change_level(local, remote)

    if change is None:
        print("You're on the latest version. Nothing to update.")
        return 0

    print(f"A newer version is available: {remote_text} "
          f"({change} update, you have {local_text}).")

    # Only act if the change meets the level you asked to be bothered at.
    if LEVELS[change] < LEVELS[level]:
        print(f"(Your update_level is '{level}', so this {change} update "
              f"won't prompt. Run with --level {change} to update it anyway.)")
        return 0

    if check_only:
        print("Run  python update.py  to install it.")
        return 0

    if assume_yes or ask_yes_no("Update now?", default=True):
        return 0 if do_update() else 1

    print("Skipped. You can update any time with:  python update.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
