from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def run(command: list[str]) -> None:
    """Run one required build step from the repository root."""
    subprocess.run(command, cwd=REPO_ROOT, check=True)


def main() -> int:
    # Quarto sets this to "1" only when rendering the complete project.
    if os.getenv("QUARTO_PROJECT_RENDER_ALL") != "1":
        print(
            "Incremental development render: "
            "skipping glossary generation and social-card pipeline."
        )
        return 0

    print("Full project render: generating glossary.")
    run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "learn_glossary.py"),
            "generate",
        ]
    )

    print("Full project render: running social-card pipeline.")
    run(
        [
            sys.executable,
            str(
                REPO_ROOT
                / "social_generator"
                / "scripts"
                / "social"
                / "run_social_pipeline.py"
            ),
        ]
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
