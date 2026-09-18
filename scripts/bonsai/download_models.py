#!/usr/bin/env python3
"""Download pinned Bonsai packings, verifying bytes before publication."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

MODELS = [
    ("prism-ml/Ternary-Bonsai-2-27B-gguf", "6ed5e12bf84b7a63069882c91dd9e9218647d17b",
     "Ternary-Bonsai-2-27B-PQ2_0.gguf", 7206168928,
     "3907dc1658db1f78a9826bf8d5bcb8dc65db0d466388937af57f2294fae62ec1"),
    ("prism-ml/Ternary-Bonsai-2-27B-gguf", "6ed5e12bf84b7a63069882c91dd9e9218647d17b",
     "Ternary-Bonsai-2-27B-PTQ1_0.gguf", 5946648928,
     "53107f530aa52eb00912263ab1ee29bd199261c87cd7b4ad4ca1318c1fe33ee3"),
    ("prism-ml/Ternary-Bonsai-2-27B-gguf-dev", "2a263ef827a2e215f3ddd14c9871a5bd1800fcbc",
     "Ternary-Bonsai-2-27B-Q2_0-prism-fork-required.gguf", 7626008928,
     "4f99aed01b8a877e153f9aa6569a4440fe17c59701cc0953e36d7f460549e70e"),
]


def verify(path, size, digest):
    if path.stat().st_size != size:
        raise RuntimeError(f"Unexpected size: {path}")
    h = hashlib.sha256()
    with path.open("rb") as stream:
        if stream.read(4) != b"GGUF":
            raise RuntimeError(f"Not a GGUF: {path}")
        stream.seek(0)
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            h.update(block)
    if h.hexdigest() != digest:
        raise RuntimeError(f"SHA256 mismatch; file retained for inspection: {path}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    args.directory.mkdir(parents=True, exist_ok=True)
    manifest = []
    for repo, revision, name, size, digest in MODELS:
        destination = args.directory / name
        url = f"https://huggingface.co/{repo}/resolve/{revision}/{name}"
        if not destination.exists():
            partial = destination.with_suffix(".gguf.partial")
            present = partial.stat().st_size if partial.exists() else 0
            if shutil.disk_usage(args.directory).free < max(0, size - present) + 4 * 1024**3:
                raise RuntimeError("Insufficient space with 4 GiB working reserve")
            print(f"Downloading {name}", flush=True)
            subprocess.run(["curl", "--fail", "--location", "--retry", "3",
                            "--continue-at", "-", "--output", str(partial), url], check=True)
            verify(partial, size, digest)
            os.replace(partial, destination)
        else:
            verify(destination, size, digest)
        print(f"Verified {name}: {digest}", flush=True)
        manifest.append(dict(file=name, bytes=size, sha256=digest, source=url))
    temporary = args.directory / "verified-models.json.tmp"
    temporary.write_text(json.dumps(manifest, indent=2) + "\n")
    os.replace(temporary, args.directory / "verified-models.json")


if __name__ == "__main__":
    main()
