#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path

IMAGE_FILE_MACHINE_AMD64 = 0x8664
PE32_PLUS = 0x20B
IMAGE_SUBSYSTEM_WINDOWS_GUI = 2


def inspect_pe(data: bytes) -> dict[str, int]:
    if len(data) < 0x40 or data[:2] != b"MZ":
        raise ValueError("missing DOS MZ header")
    pe_offset = struct.unpack_from("<I", data, 0x3C)[0]
    if pe_offset + 26 > len(data) or data[pe_offset:pe_offset + 4] != b"PE\0\0":
        raise ValueError("missing PE signature")
    machine, _, _, _, _, opt_size, _ = struct.unpack_from("<HHIIIHH", data, pe_offset + 4)
    opt = pe_offset + 24
    if opt + opt_size > len(data) or opt_size < 70:
        raise ValueError("truncated PE optional header")
    magic = struct.unpack_from("<H", data, opt)[0]
    subsystem = struct.unpack_from("<H", data, opt + 68)[0]
    return {"machine": machine, "magic": magic, "subsystem": subsystem}


def validate(path: Path) -> dict[str, object]:
    data = path.read_bytes()
    info = inspect_pe(data)
    if info["machine"] != IMAGE_FILE_MACHINE_AMD64:
        raise ValueError(f"unexpected machine 0x{info['machine']:04x}")
    if info["magic"] != PE32_PLUS:
        raise ValueError(f"expected PE32+, got 0x{info['magic']:x}")
    if info["subsystem"] != IMAGE_SUBSYSTEM_WINDOWS_GUI:
        raise ValueError(f"expected Windows GUI subsystem 2, got {info['subsystem']}")
    if len(data) < 1_000_000:
        raise ValueError("portable executable is unexpectedly small")
    return {
        "path": str(path),
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        **info,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("exe", type=Path)
    args = ap.parse_args()
    try:
        report = validate(args.exe)
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 2
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
