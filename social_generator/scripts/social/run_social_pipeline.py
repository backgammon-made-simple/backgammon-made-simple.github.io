from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RENDERER = ROOT / "scripts" / "social" / "render_cards.py"
INTEGRATION_VALIDATOR = (
    ROOT / "scripts" / "social" / "validate_social_integration.R"
)


def run(command: list[str]) -> None:
    print("+", " ".join(command), flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


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

    rscript = shutil.which("Rscript")
    if rscript is None:
        print(
            "ERROR: Rscript was not found on PATH. "
            "Install R or run this from an R-enabled shell.",
            file=sys.stderr,
        )
        return 1

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
