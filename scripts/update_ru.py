#!/usr/bin/env python3
"""Sync the upstream Russia domain list into a Clash classical text ruleset."""
from pathlib import Path
import re
import time
from urllib.request import Request, urlopen

SOURCE = "https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/meta/geo/geosite/category-ru.list"
TARGET = Path(__file__).resolve().parents[1] / "list" / "ru.list"


def convert(text: str) -> str:
    rules = set()
    for line in text.splitlines():
        value = line.split("#", 1)[0].strip().lower()
        if not value:
            continue
        kind = "DOMAIN-SUFFIX" if value.startswith("+.") else "DOMAIN"
        domain = value[2:] if kind == "DOMAIN-SUFFIX" else value
        domain = domain.encode("idna").decode("ascii")
        labels = domain.split(".")
        if len(domain) > 253 or not all(
            re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label)
            for label in labels
        ):
            raise ValueError("Unexpected upstream domain syntax; keeping the previous list")
        rules.add(f"{kind},{domain}")
    if len(rules) < 100 or "DOMAIN-SUFFIX,ru" not in rules:
        raise ValueError("Upstream list is incomplete; keeping the previous list")
    header = (
        "# Russia websites: Clash classical text rules\n"
        f"# Source: {SOURCE}\n"
        "# Upstream attribution: MetaCubeX/meta-rules-dat and v2fly/domain-list-community\n"
        "# Exact domains remain DOMAIN; +. domains become DOMAIN-SUFFIX.\n"
        f"# Rule count: {len(rules)}\n\n"
    )
    return header + "\n".join(sorted(rules)) + "\n"


def main() -> None:
    for attempt in range(3):
        try:
            with urlopen(Request(SOURCE, headers={"User-Agent": "garydak-clash-ru-sync/1.0"}), timeout=30) as response:
                data = response.read(2_000_001)
            if len(data) > 2_000_000:
                raise ValueError("Upstream response is unexpectedly large")
            output = convert(data.decode("utf-8-sig"))
            break
        except Exception:
            if attempt == 2:
                raise
            time.sleep(2 * (attempt + 1))
    previous = TARGET.read_text(encoding="utf-8") if TARGET.exists() else ""
    previous_count = sum(line.startswith(("DOMAIN,", "DOMAIN-SUFFIX,")) for line in previous.splitlines())
    next_count = sum(line.startswith(("DOMAIN,", "DOMAIN-SUFFIX,")) for line in output.splitlines())
    if previous_count and next_count < previous_count / 2:
        raise ValueError("Unexpected rule count drop; keeping the previous list")
    if output == previous:
        print(f"ru.list unchanged ({next_count} rules)")
        return
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    staging = TARGET.with_suffix(".list.tmp")
    staging.write_text(output, encoding="utf-8", newline="\n")
    staging.replace(TARGET)
    print(f"ru.list updated ({next_count} rules)")


if __name__ == "__main__":
    main()
