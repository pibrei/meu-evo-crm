"""
Ingest a file or a folder of .md/.txt files into the kb-search service.

Examples:
    python ingest.py ./docs --url http://localhost:8080 --api-key SECRET
    KB_API_KEY=SECRET python ingest.py procedimentos.md --url http://localhost:8080
"""
import argparse
import glob
import os
import sys

import httpx


def collect_files(path: str) -> list[str]:
    if os.path.isdir(path):
        files: list[str] = []
        for ext in ("*.md", "*.txt"):
            files += glob.glob(os.path.join(path, "**", ext), recursive=True)
        return sorted(files)
    return [path]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("path", help="file or directory of .md/.txt files")
    ap.add_argument("--url", default="http://localhost:8080")
    ap.add_argument("--api-key", default=os.environ.get("KB_API_KEY", ""))
    ap.add_argument("--no-replace", action="store_true", help="append instead of replacing each source")
    args = ap.parse_args()

    files = collect_files(args.path)
    if not files:
        print("no .md/.txt files found")
        sys.exit(1)

    base = args.path if os.path.isdir(args.path) else os.path.dirname(args.path) or "."
    documents = []
    for f in files:
        with open(f, encoding="utf-8") as fh:
            content = fh.read()
        source = os.path.relpath(f, base)
        documents.append({"content": content, "source": source, "metadata": {"file": source}})

    headers = {"X-API-Key": args.api_key} if args.api_key else {}
    resp = httpx.post(
        f"{args.url.rstrip('/')}/ingest",
        json={"documents": documents, "replace": not args.no_replace},
        headers=headers,
        timeout=600,
    )
    resp.raise_for_status()
    print(resp.json())


if __name__ == "__main__":
    main()
