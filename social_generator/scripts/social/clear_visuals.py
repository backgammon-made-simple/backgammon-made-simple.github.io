from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "site" / "assets" / "social" / "social-cards.yml"


def main() -> int:
    raw = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))

    if not isinstance(raw, dict) or not isinstance(raw.get("cards"), list):
        raise SystemExit("Invalid social-cards.yml structure")

    changed = 0

    for card in raw["cards"]:
        if card.get("visual", "") != "":
            card["visual"] = ""
            changed += 1

    MANIFEST.write_text(
        yaml.safe_dump(
            raw,
            sort_keys=False,
            allow_unicode=True,
            width=1000,
        ),
        encoding="utf-8",
    )

    print(f"Set visual: \"\" on {changed} card record(s).")
    print(
        "Also update the R content generator so future manifests "
        "continue to emit an empty visual field."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
