#!/usr/bin/env python3
"""Bind one reviewed official clock-gate instance to the actual 12-track cell.

Reads the exact official source and writes a private copy. No behavioral gate,
FPGA define, shared-library edit, or unreviewed source revision is accepted.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

EXPECTED_SOURCE_SHA256 = "dd95980eed40125ceeba19d69f165b829608b4e88ff489ef87f05ca9d3a6871a"
OLD_CELL = "CLKLANAQV4_8TR40"
NEW_CELL = "CLKLANAQV4_12TR40"
MODULE = "GENERIC_CLOCKGATE_RVT"


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def existing(path):
    p = Path(path).resolve()
    if not p.is_file() or not p.stat().st_size:
        raise ValueError("Missing/empty input: {}".format(p))
    return p


def module_span(text, name):
    matches = list(re.finditer(r"(?ms)^\s*module\s+" + re.escape(name) + r"\b.*?^\s*endmodule\b", text))
    if len(matches) != 1:
        raise ValueError("Expected exactly one module " + name)
    return matches[0]


def transform(text):
    """Structural transformation only; public entry point additionally enforces SHA."""
    region = module_span(text, MODULE)
    body = region.group(0)
    instances = list(re.finditer(r"\b" + OLD_CELL + r"\s+u_donttouch_CLOCKGATE\s*\((.*?)\)\s*;", body, re.S))
    if len(instances) != 1 or len(re.findall(r"\b" + OLD_CELL + r"\b", body)) != 1:
        raise ValueError("Reviewed clock-gate instance is absent or ambiguous")
    inst = instances[0]
    ports = re.findall(r"\.([A-Za-z_][A-Za-z0-9_]*)\s*\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*\)", inst.group(1))
    if len(ports) != 4 or dict(ports) != {"Q": "ECK", "E": "E", "TE": "SE", "CK": "CK"}:
        raise ValueError("Clock-gate pin mapping differs from reviewed Q/E/TE/CK binding")
    # Only this cell-reference token changes. All comments, other modules, pins,
    # FPGA conditionals and instance names remain byte-identical.
    start = region.start() + inst.start()
    return text[:start] + NEW_CELL + text[start + len(OLD_CELL):]


def prepare(source, std_model, std_db, std_library, destination):
    source, std_model, std_db = existing(source), existing(std_model), existing(std_db)
    out = Path(destination).resolve()
    if out.exists():
        raise ValueError("Use a new private output directory; shared source is never overwritten")
    if sha(source) != EXPECTED_SOURCE_SHA256:
        raise ValueError("Official GENERIC_RVT_SMIC.v SHA differs from the reviewed actual platform")
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.-]*", std_library):
        raise ValueError("Explicit actual standard-library name required")
    model_region = module_span(std_model.read_text(errors="replace"), NEW_CELL).group(0)
    header = re.search(r"\bmodule\s+" + NEW_CELL + r"\s*\(([^;]*)\)\s*;", model_region)
    if not header or {x.strip() for x in header[1].split(",")} != {"Q", "CK", "E", "TE"}:
        raise ValueError("Actual 12-track model does not expose exactly Q/CK/E/TE")
    # latin-1 is a lossless byte mapping, retaining legacy source encodings and
    # CRLF/LF exactly; only the ASCII cell-reference token is changed.
    original = source.read_bytes().decode("latin-1")
    changed = transform(original)
    out.mkdir(parents=True)
    overlay = out / "GENERIC_RVT_SMIC.v"
    overlay.write_bytes(changed.encode("latin-1"))
    guard = {"schema_version": 1, "status": "prepared_requires_actual_model_test", "formal_accepted": False,
             "source": str(source), "source_sha256": sha(source),
             "overlay": str(overlay), "overlay_sha256": sha(overlay),
             "selected_module": MODULE, "old_cell": OLD_CELL, "selected_cell": NEW_CELL,
             "instance": "u_donttouch_CLOCKGATE", "pin_mapping": {"Q": "ECK", "E": "E", "TE": "SE", "CK": "CK"},
             "standard_cell_model": str(std_model), "standard_cell_model_sha256": sha(std_model),
             "standard_cell_db": str(std_db), "standard_cell_db_sha256": sha(std_db), "standard_library": std_library,
             "generator_sha256": sha(__file__), "equivalence_test_passed": False,
             "equivalence_scope": "adapted wrapper vs actual selected 12-track model plus E/TE functional checks; not timing/power equivalence to unavailable 8-track model",
             "changes": "one physical cell reference token only; no FPGA/behavioral substitution",
             "other_generic_modules": re.findall(r"(?m)^\s*module\s+(GENERIC_[A-Za-z0-9_]+)", original),
             "reachability_review_required": "Only the selected reachable GENERIC view may be compiled; any other reachable primitive must resolve to the actual selected technology library"}
    (out / "prepared_guard.json").write_text(json.dumps(guard, indent=2) + "\n")
    # Explicit actual-library assertion for a new configuration's setup script.
    assertion = ("set selected_clockgate [get_lib_cells -quiet {" + std_library + "/" + NEW_CELL + "}]\n"
                 "if {[sizeof_collection $selected_clockgate] != 1} { error {Actual selected library lacks reviewed 12-track clock-gate cell} }\n")
    (out / "assert_clockgate_library.tcl").write_text(assertion)
    return {"overlay": str(overlay), "prepared_guard": str(out / "prepared_guard.json"), "formal_accepted": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True)
    parser.add_argument("--std-model", required=True)
    parser.add_argument("--std-db", required=True)
    parser.add_argument("--std-library", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    try:
        print(json.dumps(prepare(args.source, args.std_model, args.std_db, args.std_library, args.out), indent=2))
        return 0
    except (ValueError, OSError) as exc:
        print("Clock-gate binding failed: {}".format(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
