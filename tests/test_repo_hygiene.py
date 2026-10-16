"""Guards against committing secrets."""

import re

from copilot.config import PROJECT_ROOT

SECRET_NAME = re.compile(r"(KEY|TOKEN|SECRET|PASSWORD)$")
SECRET_VALUE = re.compile(r"(sk-[A-Za-z0-9_-]{10,}|lsv2_[A-Za-z0-9_]{10,})")


def test_env_example_contains_no_secret_values():
    for n, line in enumerate((PROJECT_ROOT / ".env.example").read_text(encoding="utf-8").splitlines(), 1):
        if "=" not in line or line.lstrip().startswith("#"):
            continue
        name, value = (s.strip() for s in line.split("=", 1))
        assert not (SECRET_NAME.search(name) and value), (
            f".env.example line {n}: {name} has a value - secrets belong in .env, not the example file"
        )
        assert not SECRET_VALUE.search(value), f".env.example line {n} looks like it contains a key"


def test_env_file_is_git_ignored():
    patterns = (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert ".env" in patterns
