"""Show that the built manifest fails OWN-01 when meta.owner is removed.

The step passes only when the gate fails for that reason. It does not change
the project files.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import governance_check as gate


def without_owner(manifest: dict) -> dict:
    node = manifest["nodes"]["model.arr_semantic_layer_lab.fct_arr_snapshot"]
    for meta in (node.get("meta"), node.get("config", {}).get("meta")):
        if isinstance(meta, dict):
            meta.pop("owner", None)
    return manifest


def failing_pairs(summary: dict) -> set[tuple[str, str]]:
    return {
        (check["rule_id"], check["node"])
        for check in summary["checks"]
        if check["status"] == "fail"
    }


def main() -> int:
    manifest_path = ROOT / "target" / "manifest.json"
    if not manifest_path.exists():
        print("target/manifest.json is missing. Run make build first.", file=sys.stderr)
        return 1
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    summary = gate.summarize(
        gate.evaluate(
            without_owner(manifest),
            gate.load_yaml(ROOT / "governance" / "policy.yml"),
            gate.validate_exceptions(
                gate.load_yaml(ROOT / "governance" / "exceptions.yml"),
                gate.load_yaml(ROOT / "governance" / "policy.yml"),
            ),
        )
    )
    gate.print_human(summary)
    expected = {("OWN-01", "fct_arr_snapshot")}
    found = failing_pairs(summary)
    if found != expected:
        print(f"Expected failures {expected}, got {found}.", file=sys.stderr)
        return 1
    print()
    print("Evidence confirmed: OWN-01 fct_arr_snapshot")
    return 0


if __name__ == "__main__":
    sys.exit(main())
