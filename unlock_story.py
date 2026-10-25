#!/usr/bin/env python3
"""Set the 16 observed SpeedRunners story markers to 0x04, with backups.

The script is intentionally conservative and supports only the version-5 file
layout observed on 2026-10-25. XP changes only when requested; reward records
are preserved.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import struct
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


EXPECTED_VERSION = 5
VERSION_OFFSET = 1
XP_OFFSET = 5
REWARD_COUNT_OFFSET = 11
REWARDS_OFFSET = 15
REWARD_RECORD_SIZE = 6
CHAPTER_COUNT = 4
MARKERS_PER_CHAPTER = 4
CHAPTER_RECORD_SIZE = 8  # int32 difficulty + four one-byte markers
MARKER_VALUE = 4
INT32_MAX = 2_147_483_647


class SaveFormatError(Exception):
    """Raised when a save does not match the layout this script understands."""


@dataclass
class PreparedSave:
    path: Path
    original: bytes
    modified: bytes
    xp: int
    target_xp: int
    reward_count: int
    marker_offsets: list[int]
    old_markers: list[int]


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def prepare(path: Path, add_xp: int = 0, set_xp: int | None = None) -> PreparedSave:
    if not path.is_file():
        raise SaveFormatError(f"File non trovato: {path}")

    original = path.read_bytes()
    minimum_size = REWARDS_OFFSET
    if len(original) < minimum_size:
        raise SaveFormatError(f"File troppo corto per essere un salvataggio riconosciuto: {path}")

    version = struct.unpack_from("<i", original, VERSION_OFFSET)[0]
    if version != EXPECTED_VERSION:
        raise SaveFormatError(
            f"Versione {version} non supportata in {path}; questa guida riconosce solo la versione {EXPECTED_VERSION}."
        )

    reward_count = struct.unpack_from("<i", original, REWARD_COUNT_OFFSET)[0]
    if reward_count < 0:
        raise SaveFormatError(f"Numero di ricompense negativo in {path}.")

    story_start = REWARDS_OFFSET + reward_count * REWARD_RECORD_SIZE
    expected_size = story_start + CHAPTER_COUNT * CHAPTER_RECORD_SIZE
    if len(original) != expected_size:
        raise SaveFormatError(
            f"Dimensione inattesa in {path}: {len(original)} byte; per versione 5 e "
            f"{reward_count} ricompense ci si aspettavano {expected_size}. Il file non è stato modificato."
        )

    xp = struct.unpack_from("<i", original, XP_OFFSET)[0]
    if xp < 0:
        raise SaveFormatError(f"Valore XP negativo inatteso in {path}.")
    target_xp = set_xp if set_xp is not None else xp + add_xp
    if target_xp < 0 or target_xp > INT32_MAX:
        raise SaveFormatError(
            f"Gli XP risultanti ({target_xp}) non rientrano nell'intervallo supportato da questo formato."
        )

    marker_offsets: list[int] = []
    old_markers: list[int] = []
    for chapter in range(CHAPTER_COUNT):
        first_marker = story_start + chapter * CHAPTER_RECORD_SIZE + 4
        for marker_index in range(MARKERS_PER_CHAPTER):
            offset = first_marker + marker_index
            marker_offsets.append(offset)
            old_markers.append(original[offset])

    modified = bytearray(original)
    struct.pack_into("<i", modified, XP_OFFSET, target_xp)
    for offset in marker_offsets:
        modified[offset] = MARKER_VALUE

    return PreparedSave(
        path=path,
        original=original,
        modified=bytes(modified),
        xp=xp,
        target_xp=target_xp,
        reward_count=reward_count,
        marker_offsets=marker_offsets,
        old_markers=old_markers,
    )


def make_backup(path: Path) -> Path:
    base = Path(str(path) + ".bak")
    if not base.exists():
        backup = base
    else:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = Path(f"{path}.{stamp}.bak")
        suffix = 1
        while backup.exists():
            backup = Path(f"{path}.{stamp}-{suffix}.bak")
            suffix += 1

    with backup.open("xb") as stream:
        stream.write(path.read_bytes())
        stream.flush()
        os.fsync(stream.fileno())
    return backup


def replace_safely(item: PreparedSave) -> None:
    old_mode = item.path.stat().st_mode
    file_descriptor, temp_name = tempfile.mkstemp(
        prefix=f".{item.path.name}.", suffix=".tmp", dir=item.path.parent
    )
    try:
        with os.fdopen(file_descriptor, "wb") as stream:
            stream.write(item.modified)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temp_name, old_mode)
        os.replace(temp_name, item.path)
    except Exception:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Mostra o modifica solo i 16 indicatori della storia nel salvataggio SpeedRunners v5."
    )
    xp_options = parser.add_mutually_exclusive_group()
    xp_options.add_argument(
        "--add-xp",
        type=int,
        metavar="N",
        help="Aggiunge N XP al valore presente (intero positivo; lascia invariati gli XP se omesso).",
    )
    xp_options.add_argument(
        "--set-xp",
        type=int,
        metavar="N",
        help="Imposta il totale XP a N (intero da 0 a 2147483647).",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Applica le modifiche dopo aver creato copie .bak. Senza questa opzione esegue solo una verifica.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Esplicita la modalità di sola lettura (è già la modalità predefinita).",
    )
    parser.add_argument("files", nargs="+", type=Path, help="Uno o più file ProgressionStore da controllare.")
    args = parser.parse_args()

    if args.apply and args.dry_run:
        parser.error("Scegli --apply oppure --dry-run, non entrambi.")
    if args.add_xp is not None and args.add_xp < 1:
        parser.error("--add-xp deve essere un intero maggiore di zero.")
    if args.set_xp is not None and not 0 <= args.set_xp <= INT32_MAX:
        parser.error("--set-xp deve essere compreso tra 0 e 2147483647.")

    prepared: list[PreparedSave] = []
    try:
        # Validate every input before creating backups or writing any file.
        for path in args.files:
            prepared.append(prepare(path, args.add_xp or 0, args.set_xp))
    except (OSError, SaveFormatError) as error:
        print(f"ERRORE: {error}", file=sys.stderr)
        return 2

    for item in prepared:
        desired = [MARKER_VALUE] * len(item.marker_offsets)
        changed = sum(old != MARKER_VALUE for old in item.old_markers)
        print(f"File: {item.path}")
        print(f"  Formato: v{EXPECTED_VERSION}; dimensione: {len(item.original)} byte")
        print(f"  XP: {item.xp} -> {item.target_xp}; record ricompense: {item.reward_count}")
        print(f"  Indicatori: {item.old_markers} -> {desired} ({changed} da cambiare)")
        print(f"  SHA-256 attuale: {sha256(item.original)}")

    if not args.apply:
        print("\nSola lettura: nessun file è stato modificato. Per applicare usa --apply.")
        return 0

    backups: list[tuple[PreparedSave, Path]] = []
    try:
        for item in prepared:
            backups.append((item, make_backup(item.path)))
        for item, _backup in backups:
            replace_safely(item)
    except OSError as error:
        print(f"ERRORE durante la scrittura: {error}", file=sys.stderr)
        print("Le copie di sicurezza create sono:", file=sys.stderr)
        for _item, backup in backups:
            print(f"  {backup}", file=sys.stderr)
        print("Se un file era già stato aggiornato, ripristinalo dalla sua copia .bak.", file=sys.stderr)
        return 3

    for item, backup in backups:
        print(f"Aggiornato: {item.path}")
        print(f"  Backup: {backup}")
        print(f"  SHA-256 nuovo: {sha256(item.modified)}")
    print("\nOra avvia il gioco e controlla gli indicatori della schermata Chapter Select.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
