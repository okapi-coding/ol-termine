#!/usr/bin/env python3
"""Generiert die statischen data/fixtures-<jahr>.json fuer GitHub Pages.

Wird vom GitHub-Actions-Workflow (.github/workflows/update-data.yml)
periodisch ausgefuehrt, kann aber auch lokal laufen:

    python3 update_data.py

Holt jeweils das aktuelle Jahr bis das nächste Jahr (passend zur Jahresauswahl
im Frontend), parst und geocodiert, und schreibt die Ergebnisse nach data/.

Vorher wird bei Bedarf (fehlt oder aelter als OMAP_MAX_AGE_DAYS) die
Kartenliste von omap.ch nach omap-maps.json geholt. Erzwingen mit:

    python3 update_data.py --omap
"""
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fixtures_lib import OMAP_FILE, OMAP_LIST_URL, fetch_fixtures, fetch_omap_maps

DATA_DIR = Path(__file__).parent / "data"
OMAP_MAX_AGE_DAYS = 7


def omap_is_stale():
    try:
        generated = datetime.fromisoformat(json.loads(OMAP_FILE.read_text())["generated_at"])
    except (OSError, ValueError, KeyError):
        return True
    return datetime.now(timezone.utc) - generated > timedelta(days=OMAP_MAX_AGE_DAYS)


def update_omap():
    print("Hole Kartenliste von omap.ch ...", file=sys.stderr)
    try:
        maps = fetch_omap_maps()
    except Exception as exc:  # noqa: BLE001 - alte Datei weiterverwenden
        print(f"  Fehler: {exc} (verwende bestehende {OMAP_FILE.name})", file=sys.stderr)
        return
    if len(maps) < 1000:  # Schutz gegen halb geladene/umgebaute Seite
        print(f"  Nur {len(maps)} Karten gefunden, {OMAP_FILE.name} bleibt unveraendert", file=sys.stderr)
        return
    payload = {
        "source": OMAP_LIST_URL,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "count": len(maps),
        "maps": maps,
    }
    OMAP_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=1))
    print(f"  {len(maps)} Karten -> {OMAP_FILE.name}", file=sys.stderr)


def main():
    if "--omap" in sys.argv or omap_is_stale():
        update_omap()

    DATA_DIR.mkdir(exist_ok=True)
    current_year = datetime.now().year
    years = range(current_year, current_year + 2)  # aktuelles Jahr und nächstes Jahr
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    for year in years:
        print(f"Hole Termine {year} ...", file=sys.stderr)
        try:
            events = fetch_fixtures(year)
        except Exception as exc:  # noqa: BLE001 - ein Jahr soll die anderen nicht blockieren
            print(f"  Fehler bei {year}: {exc}", file=sys.stderr)
            continue

        payload = {
            "year": str(year),
            "count": len(events),
            "generated_at": generated_at,
            "events": events,
        }
        out_file = DATA_DIR / f"fixtures-{year}.json"
        out_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
        print(f"  {len(events)} Termine -> {out_file.name}", file=sys.stderr)


if __name__ == "__main__":
    main()
