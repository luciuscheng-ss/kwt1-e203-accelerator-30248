"""Streaming VCD window extraction and declaration/activity inventory, Python 3.6+."""
from decimal import Decimal
import re

SCALES = {"s": Decimal("1e9"), "ms": Decimal("1e6"), "us": Decimal("1e3"),
          "ns": Decimal(1), "ps": Decimal("1e-3"), "fs": Decimal("1e-6")}


def canonical(name):
    return name[1:] if name.startswith("\\") else name


def read_header(stream):
    lines, scopes, definitions, by_path = [], [], {}, {}
    statement, header_bytes = "", 0
    for line in stream:
        lines.append(line)
        header_bytes += len(line)
        if header_bytes > 64 * 1024 * 1024:
            raise ValueError("VCD header exceeds 64 MiB")
        statement += " " + line.strip()
        while "$end" in statement:
            # $enddefinitions is itself a directive, not the terminator token.
            match = re.search(r"\$end(?:\s|$)", statement)
            if not match:
                break
            command, statement = statement[:match.start()].strip(), statement[match.end():]
            words = command.split()
            if not words:
                continue
            if words[0] == "$scope":
                scopes.append(canonical(words[2]))
            elif words[0] == "$upscope":
                if not scopes:
                    raise ValueError("VCD scope underflow")
                scopes.pop()
            elif words[0] == "$var":
                if len(words) < 5:
                    raise ValueError("malformed VCD declaration")
                path = "/".join(scopes + [canonical(words[4])])
                entry = {"path": path, "type": words[1], "width": int(words[2]), "code": words[3]}
                by_path[path] = entry
                definitions.setdefault(words[3], []).append(entry)
            elif words[0] == "$enddefinitions":
                header = "".join(lines)
                unit = re.search(r"\$timescale\s+([0-9.]+)\s*(s|ms|us|ns|ps|fs)\s+\$end", header)
                if not unit:
                    raise ValueError("VCD timescale absent/unsupported")
                return header, Decimal(unit[1]) * SCALES[unit[2]], definitions, by_path
    raise ValueError("VCD enddefinitions missing")


def tokens(stream):
    for line in stream:
        for word in line.split():
            yield word


def groups(stream):
    timestamp, events, mode = 0, [], None
    iterator = iter(tokens(stream))
    for word in iterator:
        if word.startswith("#"):
            next_time = int(word[1:])
            if next_time < timestamp:
                raise ValueError("VCD timestamp moves backwards")
            if next_time != timestamp:
                if events or timestamp != 0:
                    yield timestamp, events
                timestamp, events = next_time, []
        elif word in ("$dumpvars", "$dumpon", "$dumpoff", "$dumpall"):
            mode = word
            events.append(("control", word, None, None))
        elif word == "$end":
            mode = None
        elif word.startswith("$"):
            for tail in iterator:
                if tail == "$end":
                    break
        elif word and word[0] in "01xXzZ" and len(word) > 1:
            events.append(("value", word[1:], word[0].lower(), mode))
        elif word and word[0] in "bBrR":
            code = next(iterator)
            events.append(("value", code, word.lower(), mode))
        else:
            raise ValueError("unsupported/malformed VCD token: " + word[:80])
    yield timestamp, events


def bits(value, width):
    if value.startswith("r"):
        return None
    raw = value[1:] if value.startswith("b") else value
    fill = raw[0] if raw and raw[0] in "xz" else "0"
    return raw.rjust(width, fill)


def unknown(value, width):
    raw = bits(value, width)
    return raw is not None and ("x" in raw or "z" in raw)


def emit_value(code, value):
    return value + (" " if value.startswith(("b", "r")) else "") + code + "\n"


def scan_and_crop(source, destination, start_ns, end_ns, tracked_paths, rebase=False):
    if source.resolve() == destination.resolve():
        raise ValueError("refusing to overwrite original activity")
    with source.open(encoding="ascii", errors="strict") as stream:
        header, scale, definitions, by_path = read_header(stream)
        start_exact, end_exact = Decimal(str(start_ns)) / scale, Decimal(str(end_ns)) / scale
        start, end = int(start_exact.to_integral_value()), int(end_exact.to_integral_value())
        if abs(Decimal(start) - start_exact) > Decimal("0.001") or abs(Decimal(end) - end_exact) > Decimal("0.001"):
            raise ValueError("log window cannot be represented in VCD ticks; increase timing-log precision")
        if start < 0 or end <= start:
            raise ValueError("invalid window")
        def output_tick(timestamp):
            return timestamp - start if rebase else timestamp
        tracked = {by_path[path]["code"] for path in tracked_paths if path in by_path}
        widths = {code: entries[0]["width"] for code, entries in definitions.items()}
        current, stats, changes, ever_unknown = {}, {}, set(), set()
        started, finished, dumping = False, False, True
        start_control, end_control, gaps = [], [], []
        initial_snapshot_mode = None
        raw_first, raw_last, previous_time = None, 0, 0

        def initialize(out):
            nonlocal started
            started = True
            out.write("#%d\n$dumpvars\n" % output_tick(start))
            for code in sorted(current):
                out.write(emit_value(code, current[code]))
                if unknown(current[code], widths[code]):
                    ever_unknown.add(code)
            out.write("$end\n")
            for code in tracked:
                value = current.get(code)
                stats[code] = {"initial": value, "last": value, "last_time": start, "changes": 0,
                               "bit_flips_known": 0, "unknown_ticks": 0, "rising_edges": 0,
                               "first_rise": None, "last_rise": None, "min_period_ticks": None, "max_period_ticks": None}
                if value is not None and bits(value, widths[code]) == "1":
                    stats[code]["rising_edges"] = 1
                    stats[code]["first_rise"] = stats[code]["last_rise"] = start

        def track(code, value, timestamp):
            old = current.get(code)
            if old != value:
                changes.add(code)
            if unknown(value, widths[code]):
                ever_unknown.add(code)
            if code in stats:
                entry = stats[code]
                if old is None or unknown(old, widths[code]):
                    entry["unknown_ticks"] += timestamp - entry["last_time"]
                if old != value:
                    entry["changes"] += 1
                a = bits(old, widths[code]) if old is not None else None
                b = bits(value, widths[code])
                if a is not None and b is not None and not any(x in a + b for x in "xz"):
                    entry["bit_flips_known"] += sum(x != y for x, y in zip(a, b))
                if widths[code] == 1 and a == "0" and b == "1":
                    if entry["last_rise"] is not None:
                        period = timestamp - entry["last_rise"]
                        entry["min_period_ticks"] = period if entry["min_period_ticks"] is None else min(entry["min_period_ticks"], period)
                        entry["max_period_ticks"] = period if entry["max_period_ticks"] is None else max(entry["max_period_ticks"], period)
                    entry["rising_edges"] += 1
                    if entry["first_rise"] is None:
                        entry["first_rise"] = timestamp
                    entry["last_rise"] = timestamp
                entry["last"], entry["last_time"] = value, timestamp
            current[code] = value

        with destination.open("w", encoding="ascii") as out:
            out.write(header)
            for timestamp, events in groups(stream):
                raw_first = timestamp if raw_first is None else raw_first
                raw_last = timestamp
                if not dumping and previous_time < end and timestamp > start:
                    gap_start, gap_end = max(previous_time, start), min(timestamp, end)
                    if gap_end > gap_start:
                        gaps.append([gap_start, gap_end])
                previous_time = timestamp
                if timestamp < start:
                    for kind, code, value, mode in events:
                        if kind == "control":
                            if code == "$dumpoff":
                                dumping = False
                            elif code == "$dumpon":
                                dumping = True
                        elif code in widths and mode != "$dumpoff":
                            current[code] = value
                    continue
                if not started:
                    if timestamp == start:
                        start_control = [code for kind, code, _, _ in events if kind == "control"]
                        if not dumping or not current:
                            initial_snapshot_mode = "post_dumpon_snapshot_without_preedge_history"
                            for kind, code, value, mode in events:
                                if kind == "control":
                                    if code == "$dumpon":
                                        dumping = True
                                    elif code == "$dumpoff":
                                        dumping = False
                                elif code in widths and mode != "$dumpoff":
                                    current[code] = value
                            initialize(out)
                            continue
                    initial_snapshot_mode = "preedge_reconstructed_then_window_events"
                    initialize(out)
                if timestamp >= end:
                    if timestamp == end:
                        end_control = [code for kind, code, _, _ in events if kind == "control"]
                    if not finished:
                        out.write("#%d\n" % output_tick(end))
                        finished = True
                    continue
                values = []
                for kind, code, value, mode in events:
                    if kind == "control":
                        if code == "$dumpoff":
                            dumping = False
                        elif code == "$dumpon":
                            dumping = True
                    elif code in widths and mode != "$dumpoff":
                        track(code, value, timestamp)
                        values.append((code, value))
                if values:
                    out.write("#%d\n" % output_tick(timestamp))
                    for code, value in values:
                        out.write(emit_value(code, value))
            if not started or raw_last < end:
                raise ValueError("VCD ends before the requested task interval")
            if not finished:
                out.write("#%d\n" % output_tick(end))
            for code, entry in stats.items():
                if entry["last"] is None or unknown(entry["last"], widths[code]):
                    entry["unknown_ticks"] += end - entry["last_time"]
                entry["unknown_duration_ns"] = float(Decimal(entry["unknown_ticks"]) * scale)
                if entry["rising_edges"] > 1:
                    entry["mean_rising_period_ns"] = float(Decimal(entry["last_rise"] - entry["first_rise"]) * scale / (entry["rising_edges"] - 1))
        return {"timescale_ns": str(scale), "start_tick": start, "end_tick": end,
                "output_start_tick": output_tick(start), "output_end_tick": output_tick(end),
                "origin_shift_ticks": start if rebase else 0,
                "raw_first_tick": raw_first, "raw_last_tick": raw_last,
                "initial_snapshot_mode": initial_snapshot_mode,
                "start_dump_controls": start_control, "end_dump_controls": end_control,
                "dump_off_gaps_within_window": gaps, "unique_vcd_ids": len(definitions),
                "definitions": definitions, "by_path": by_path, "observed_ids": set(current),
                "changed_ids": changes, "unknown_ids": ever_unknown, "tracked_stats": stats}
