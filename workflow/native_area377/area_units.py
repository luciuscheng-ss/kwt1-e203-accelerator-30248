#!/usr/bin/env python3
"""Cross-check library raw cell area against LEF SIZE and explicit macro evidence.

Python 3.6 standard library. prepare writes a read-only DC probe; check binds its
outputs to unchanged inputs and reports conversion ratios, coverage and outliers.
No technology, corner, official acceptance or mm2 unit is assumed by default.
"""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import re
import statistics
import sys
import uuid

NUMBER = r"[-+]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][-+]?[0-9]+)?"


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def required_file(path):
    p = Path(path).resolve()
    if not p.is_file() or not p.stat().st_size:
        raise ValueError("Required file is missing/empty: {}".format(p))
    return p


def dump(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def tcl(value):
    value = str(value)
    for before, after in (("\\", "\\\\"), ('"', '\\"'), ("$", "\\$"), ("[", "\\["),
                          ("]", "\\]"), ("\n", "\\n"), ("\r", "\\r")):
        value = value.replace(before, after)
    return '"' + value + '"'


def tcl_list(values):
    return "[list {}]".format(" ".join(tcl(v) for v in values))


def parse_lef(path):
    text = re.sub(r"(?m)#.*$", "", Path(path).read_text(errors="replace"))
    blocks = list(re.finditer(r"(?ms)^\s*MACRO\s+(\S+)\s*\n(.*?)^\s*END\s+\1\s*$", text))
    declared = len(re.findall(r"(?m)^\s*MACRO\s+", text))
    if not blocks or len(blocks) != declared:
        raise ValueError("LEF MACRO blocks are missing or incomplete; refusing partial parsing")
    cells = {}
    for block in blocks:
        name, body = block.group(1), block.group(2)
        if name in cells or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_$]*", name):
            raise ValueError("Duplicate/unsupported LEF macro name: {}".format(name))
        sizes = re.findall(r"\bSIZE\s+(" + NUMBER + r")\s+BY\s+(" + NUMBER + r")\s*;", body)
        if len(sizes) != 1:
            raise ValueError("Expected one SIZE for LEF macro {}".format(name))
        width, height = map(float, sizes[0])
        if not all(math.isfinite(v) and v > 0 for v in (width, height)):
            raise ValueError("Nonpositive/nonfinite LEF dimensions: {}".format(name))
        cells[name] = {"width_um": width, "height_um": height, "area_um2": width * height}
    units = re.search(r"\bDATABASE\s+MICRONS\s+(\d+)\s*;", text)
    return {"dimension_source": "LEF MACRO SIZE, dimensions in micrometres",
            "database_microns": int(units[1]) if units else None, "cells": cells}


PROBE = r'''
# Generated read-only area-unit probe. No default operating corner is selected.
set area_out __OUT__
set area_run_id __RUN_ID__
set area_std_library __STD_LIB__
set area_dbs __DBS__
set area_cells __CELLS__
set area_macros __MACROS__

proc area_main {} {
    global area_out area_run_id area_std_library area_dbs area_cells area_macros
    set datafile [file join $area_out raw_areas.tsv]
    if {[file exists $datafile] || [file exists [file join $area_out complete.txt]]} {
        error "Area probe output already exists; prepare a new directory instead of reusing stale results"
    }
    foreach db $area_dbs {
        set result [read_db $db]
        if {$result eq "0"} { error "read_db failed for $db" }
    }
    if {[sizeof_collection [get_libs -quiet $area_std_library]] != 1} {
        error "Explicit standard-cell internal library name is absent or ambiguous: $area_std_library"
    }
    set f [open $datafile w]
    puts $f "kind\tlibrary\tcell\traw_area\tstatus"
    foreach name $area_cells {
        set cell [get_lib_cells -quiet "${area_std_library}/$name"]
        set count [sizeof_collection $cell]
        if {$count == 1} {
            set area [get_attribute -quiet $cell area]
            puts $f [join [list standard_cell $area_std_library $name $area ok] "\t"]
        } else {
            puts $f [join [list standard_cell $area_std_library $name NA "missing_or_ambiguous_$count"] "\t"]
        }
    }
    foreach name $area_macros {
        set cell [get_lib_cells -quiet "*/$name"]
        set count [sizeof_collection $cell]
        if {$count == 1} {
            set full [get_object_name $cell]
            set library [string range $full 0 [expr {[string last / $full] - 1}]]
            set area [get_attribute -quiet $cell area]
            puts $f [join [list sram $library $name $area ok] "\t"]
        } else {
            puts $f [join [list sram unknown $name NA "missing_or_ambiguous_$count"] "\t"]
        }
    }
    close $f
    set f [open [file join $area_out tool_metadata.txt] w]
    foreach name {synopsys_program_name sh_product_version} {
        if {[info exists ::$name]} { puts $f "$name=[set ::$name]" }
    }
    puts $f "standard_library=$area_std_library"
    puts $f "run_id=$area_run_id"
    puts $f "formal_accepted=false"
    close $f
    set f [open [file join $area_out complete.txt] w]
    puts $f $area_run_id
    close $f
    puts "AREA_PROBE_COMPLETED $area_run_id"
}
if {[catch {area_main} message options]} {
    puts stderr "Error: AREA_PROBE_FAILED: $message"
    if {[dict exists $options -errorinfo]} { puts stderr [dict get $options -errorinfo] }
    exit 2
}
exit 0
'''


def prepare(config_path, lef_path, destination):
    config_path, lef_path = required_file(config_path), required_file(lef_path)
    out = Path(destination).resolve()
    if out.exists():
        raise ValueError("Use a fresh preparation/output directory: {}".format(out))
    config = json.loads(config_path.read_text())
    libraries = config["libraries"]
    dbs = [required_file(config_path.parent / p) for p in libraries["target_db"] + libraries["macro_db"]]
    library = libraries["operating_library"]
    if not isinstance(library, str) or not library.strip():
        raise ValueError("Config must name an explicit internal standard library")
    macros = [entry["reference"] for entry in libraries["expected_sram_cells"]]
    if len(macros) != len(set(macros)):
        raise ValueError("Duplicate configured SRAM references")
    lef = parse_lef(lef_path)
    out.mkdir(parents=True)
    dump(out / "lef_areas.json", lef)
    run_id = uuid.uuid4().hex
    replacements = {"__OUT__": tcl(out), "__RUN_ID__": tcl(run_id), "__STD_LIB__": tcl(library),
                    "__DBS__": tcl_list(dbs), "__CELLS__": tcl_list(sorted(lef["cells"])),
                    "__MACROS__": tcl_list(macros)}
    script = PROBE
    for key, value in replacements.items():
        script = script.replace(key, value)
    (out / "probe_area.tcl").write_text(script)
    inputs = [config_path, lef_path] + dbs + [Path(__file__).resolve()]
    manifest = {"schema_version": 1, "run_id": run_id, "formal_accepted": False,
                "purpose": "raw library area vs LEF physical dimensions; no official PPA acceptance",
                "standard_library": library, "macro_references": macros, "lef_cell_count": len(lef["cells"]),
                "inputs": {str(p): sha(p) for p in inputs},
                "prepared": {name: sha(out / name) for name in ("lef_areas.json", "probe_area.tcl")}}
    dump(out / "manifest.json", manifest)
    return {"status": "prepared", "lef_cells": len(lef["cells"]), "tcl": str(out / "probe_area.tcl"),
            "next": "Run dc_shell -f this Tcl, then area_units.py check DIRECTORY", "formal_accepted": False}


def check(directory, tolerance=1e-5, macro_areas=None, macro_evidence=None):
    out = Path(directory).resolve()
    manifest_path = required_file(out / "manifest.json")
    manifest = json.loads(manifest_path.read_text())
    for path, expected in manifest["inputs"].items():
        if sha(required_file(path)) != expected:
            raise ValueError("Input changed after area-probe preparation: {}".format(path))
    for name, expected in manifest["prepared"].items():
        if sha(required_file(out / name)) != expected:
            raise ValueError("Prepared artifact changed: {}".format(name))
    if required_file(out / "complete.txt").read_text().strip() != manifest["run_id"]:
        raise ValueError("Area probe completion marker does not match preparation")
    metadata = required_file(out / "tool_metadata.txt")
    raw_path = required_file(out / "raw_areas.tsv")
    lef = json.loads((out / "lef_areas.json").read_text())["cells"]
    with raw_path.open() as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        if reader.fieldnames != ["kind", "library", "cell", "raw_area", "status"]:
            raise ValueError("Unexpected raw area table header")
        rows = list(reader)
    std, macro, issues = {}, {}, []
    for row in rows:
        kind, name = row["kind"], row["cell"]
        target = std if kind == "standard_cell" else macro if kind == "sram" else None
        if target is None or name in target:
            raise ValueError("Unknown/duplicate probe row: {} {}".format(kind, name))
        target[name] = row
        if row["status"] != "ok":
            issues.append({"kind": kind, "cell": name, "problem": row["status"]})
            continue
        try:
            area = float(row["raw_area"])
        except ValueError:
            area = float("nan")
        if not math.isfinite(area) or area <= 0:
            row["status"] = "invalid_or_nonpositive_area"
            issues.append({"kind": kind, "cell": name, "problem": row["status"]})
        else:
            row["raw_area"] = area
    if set(std) != set(lef) or set(macro) != set(manifest["macro_references"]):
        raise ValueError("Probe omitted/added configured standard cells or SRAM references")
    pairs = []
    for name, dimensions in lef.items():
        row = std[name]
        if row["status"] == "ok":
            if row["library"] != manifest["standard_library"]:
                raise ValueError("Standard-cell row came from a different library")
            physical = dimensions["area_um2"]
            pairs.append(dict(cell=name, raw_area=row["raw_area"], lef_area_um2=physical,
                              raw_to_um2=physical / row["raw_area"]))
    ratios = [p["raw_to_um2"] for p in pairs]
    median = statistics.median(ratios) if ratios else None
    outliers = [p for p in pairs if abs(p["raw_to_um2"] / median - 1) > tolerance] if median else []
    std_factor_verified = len(pairs) >= 3 and not outliers
    factor = median if std_factor_verified else None
    if factor is not None and abs(factor - 1) <= tolerance:
        factor = 1.0
    refs = {}
    for item in macro_areas or []:
        name, separator, value = item.partition("=")
        if not separator or name not in macro or name in refs:
            raise ValueError("--macro-area must be a unique configured CELL=AREA_UM2")
        value = float(value)
        if not math.isfinite(value) or value <= 0:
            raise ValueError("Macro reference area must be positive and finite")
        refs[name] = value
    if refs and not macro_evidence or macro_evidence and not refs:
        raise ValueError("Provide --macro-area and --macro-evidence together")
    evidence = required_file(macro_evidence) if macro_evidence else None
    macro_checks = []
    for name in sorted(macro):
        row = macro[name]
        entry = dict(cell=name, library=row["library"], raw_area=row["raw_area"], status=row["status"],
                     reference_area_um2=refs.get(name), independently_confirmed=False)
        if name in refs and row["status"] == "ok":
            entry["reference_raw_to_um2"] = refs[name] / row["raw_area"]
            if factor is not None:
                entry["relative_error_using_standard_factor"] = abs(row["raw_area"] * factor / refs[name] - 1)
                entry["independently_confirmed"] = entry["relative_error_using_standard_factor"] <= tolerance
        macro_checks.append(entry)
    report = {"schema_version": 1, "formal_accepted": False, "standard_library": manifest["standard_library"],
              "relative_tolerance": tolerance, "lef_cells": len(lef), "matched_standard_cells": len(pairs),
              "matched_fraction": len(pairs) / len(lef), "standard_factor_verified_for_matched_cells": std_factor_verified,
              "standard_raw_area_to_um2": factor,
              "ratio_distribution": {"min": min(ratios) if ratios else None, "median": median,
                                     "max": max(ratios) if ratios else None,
                                     "max_relative_deviation_from_median": max([abs(r / median - 1) for r in ratios]) if ratios else None},
              "outliers": outliers, "issues": issues, "standard_pairs": pairs, "macro_checks": macro_checks,
              "macro_reference_note": "Explicit operator-supplied datasheet value; source file bound below; not automatically extracted or certified",
              "macro_reference_evidence": {"path": str(evidence), "sha256": sha(evidence)} if evidence else None,
              "inputs": manifest["inputs"], "artifacts": {name: sha(out / name) for name in
                  ("manifest.json", "probe_area.tcl", "lef_areas.json", "raw_areas.tsv", "tool_metadata.txt", "complete.txt")}}
    dump(out / "area_unit_comparison.json", report)
    summary = ["AREA UNIT CROSS-CHECK — NOT OFFICIAL ACCEPTANCE",
               "Standard library: {}".format(manifest["standard_library"]),
               "Matched LEF/lib cells: {}/{}".format(len(pairs), len(lef)),
               "Physical/raw area ratio min/median/max: {} / {} / {}".format(
                   report["ratio_distribution"]["min"], median, report["ratio_distribution"]["max"]),
               "Raw standard-cell area -> um2 factor: {} (verified_for_matched_cells={})".format(factor, std_factor_verified),
               "Outliers: {}; missing/invalid cells: {}".format(len(outliers), len(issues)),
               "Macro raw areas and independent physical references:"]
    for entry in macro_checks:
        summary.append("  {cell}: raw={raw_area}, reference_um2={reference_area_um2}, independently_confirmed={independently_confirmed}".format(**entry))
    summary.extend(["Do not extrapolate standard-cell unit confirmation to unreferenced SRAM libraries.",
                    "A verified um2 quantity converts to mm2 by division by 1,000,000.", "formal_accepted=false"])
    (out / "summary.txt").write_text("\n".join(summary) + "\n", encoding="utf-8")
    return {"status": "compared", "matched_standard_cells": len(pairs), "standard_raw_area_to_um2": factor,
            "outliers": len(outliers), "macro_checks": macro_checks, "report": str(out / "area_unit_comparison.json"), "formal_accepted": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action")
    sub.required = True
    ap = sub.add_parser("prepare")
    ap.add_argument("--config", required=True)
    ap.add_argument("--lef", required=True)
    ap.add_argument("--out", required=True)
    ap = sub.add_parser("check")
    ap.add_argument("directory")
    ap.add_argument("--tolerance", type=float, default=1e-5)
    ap.add_argument("--macro-area", action="append", default=[])
    ap.add_argument("--macro-evidence")
    args = parser.parse_args(argv)
    try:
        if args.action == "prepare":
            result = prepare(args.config, args.lef, args.out)
        else:
            if not math.isfinite(args.tolerance) or not 0 < args.tolerance < 0.1:
                raise ValueError("Tolerance must be finite and between 0 and 0.1")
            result = check(args.directory, args.tolerance, args.macro_area, args.macro_evidence)
        print(json.dumps(result, indent=2))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print("Area unit check failed: {}".format(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
