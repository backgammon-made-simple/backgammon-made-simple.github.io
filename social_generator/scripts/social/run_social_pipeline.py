from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SOCIAL_SCRIPTS = ROOT / "social_generator" / "scripts" / "social"
RENDERER = SOCIAL_SCRIPTS / "render_cards.py"
MANIFEST_GENERATOR = SOCIAL_SCRIPTS / "generate_social_manifest.R"
INTEGRATION_VALIDATOR = (
    SOCIAL_SCRIPTS / "validate_social_integration.R"
)


def run(command: list[str]) -> None:
    print("+", " ".join(command), flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


def find_rscript() -> str | None:
    configured = os.environ.get("RSCRIPT")
    if configured and Path(configured).is_file():
        return configured

    discovered = shutil.which("Rscript")
    if discovered:
        return discovered

    if os.name == "nt":
        program_files = Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
        candidates = sorted(
            (program_files / "R").glob("R-*/bin/Rscript.exe"),
            reverse=True,
        )
        if candidates:
            return str(candidates[0])

    return None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the complete text-only social-card validation pipeline"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Render every card instead of only changed cards",
    )
    args = parser.parse_args()

    rscript = find_rscript()
    if rscript is None:
        print(
            "ERROR: Rscript was not found on PATH. "
            "Install R or run this from an R-enabled shell.",
            file=sys.stderr,
        )
        return 1

    run([rscript, str(MANIFEST_GENERATOR)])
    run([sys.executable, str(RENDERER), "--validate-only"])
    run([rscript, str(INTEGRATION_VALIDATOR)])
    run(
        [
            sys.executable,
            str(RENDERER),
            "--all" if args.all else "--changed",
        ]
    )

    print("Text-only social-card pipeline passed.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        raise SystemExit(exc.returncode)
