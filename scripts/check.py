import subprocess
import sys

steps = [
    ["uv", "run", "ruff", "check", "."],
    ["uv", "run", "ruff", "format", "--check", "."],
    ["uv", "run", "mypy", "src"],
    ["uv", "run", "pytest"],
]
for cmd in steps:
    print(">", " ".join(cmd))
    if subprocess.run(cmd).returncode != 0:
        sys.exit(1)
print("All checks passed.")
