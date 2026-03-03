from __future__ import annotations

import argparse
import importlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Literal, Sequence


@dataclass(frozen=True)
class LoadedDocument:
    path: Path
    modified_at_utc: datetime
    text: str

    def as_dict(self) -> dict[str, str]:
        return {
            "path": str(self.path),
            "modified_at_utc": self.modified_at_utc.isoformat(),
            "text": self.text,
        }


def find_files(
    root_dir: str | Path,
    patterns: Sequence[str] = ("*.pdf",),
    recursive: bool = True,
) -> list[Path]:
    """
    Find files under root_dir matching one or more glob patterns.

    Returns files in a deterministic order:
    1) most recent modified time first
    2) path as tie-breaker
    """
    root = Path(root_dir).expanduser().resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Directory does not exist: {root}")

    matched: set[Path] = set()
    iterator_name = "rglob" if recursive else "glob"

    for pattern in patterns:
        iterator = getattr(root, iterator_name)(pattern)
        for path in iterator:
            if path.is_file():
                matched.add(path.resolve())

    return sorted(
        matched,
        key=lambda path: (-path.stat().st_mtime, str(path).lower()),
    )


def load_pdf_text(pdf_path: str | Path) -> str:
    """
    Load text from a PDF in stable page order.

    Requires: pypdf (`pip install pypdf`)
    """
    try:
        pypdf = importlib.import_module("pypdf")
        PdfReader = pypdf.PdfReader
    except ModuleNotFoundError as exc:
        raise ImportError(
            "pypdf is required for PDF extraction. Install with: pip install pypdf"
        ) from exc

    path = Path(pdf_path).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"File does not exist: {path}")

    reader = PdfReader(str(path))
    pages: list[str] = []

    for page in reader.pages:
        text = page.extract_text() or ""
        pages.append(text.strip())

    return "\n\n".join(pages).strip()


def load_documents(
    root_dir: str | Path,
    patterns: Sequence[str] = ("*.pdf",),
    recursive: bool = True,
    max_files: int | None = None,
) -> list[LoadedDocument]:
    """
    Find matching files and load their text content.

    Currently supports PDF via pypdf.
    """
    files = find_files(root_dir=root_dir, patterns=patterns, recursive=recursive)
    if max_files is not None:
        files = files[:max_files]

    loaded: list[LoadedDocument] = []
    for path in files:
        if path.suffix.lower() == ".pdf":
            text = load_pdf_text(path)
        else:
            text = path.read_text(encoding="utf-8", errors="replace")

        loaded.append(
            LoadedDocument(
                path=path,
                modified_at_utc=datetime.fromtimestamp(
                    path.stat().st_mtime, tz=timezone.utc
                ),
                text=text,
            )
        )

    return loaded


def iter_loaded_documents(
    root_dir: str | Path,
    patterns: Sequence[str] = ("*.pdf",),
    recursive: bool = True,
    max_files: int | None = None,
) -> Iterable[LoadedDocument]:
    """Generator variant of load_documents for memory-efficient processing."""
    files = find_files(root_dir=root_dir, patterns=patterns, recursive=recursive)
    if max_files is not None:
        files = files[:max_files]

    for path in files:
        if path.suffix.lower() == ".pdf":
            text = load_pdf_text(path)
        else:
            text = path.read_text(encoding="utf-8", errors="replace")

        yield LoadedDocument(
            path=path,
            modified_at_utc=datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc),
            text=text,
        )


def save_loaded_documents(
    documents: Sequence[LoadedDocument],
    output_file: str | Path,
    output_format: Literal["json", "jsonl"] = "json",
) -> Path:
    """
    Save loaded documents to disk in JSON or JSONL format.
    """
    output_path = Path(output_file).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    rows = [document.as_dict() for document in documents]

    if output_format == "json":
        payload = {
            "generated_at_utc": datetime.now(tz=timezone.utc).isoformat(),
            "count": len(rows),
            "documents": rows,
        }
        output_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    elif output_format == "jsonl":
        output_path.write_text(
            "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
            encoding="utf-8",
        )
    else:
        raise ValueError("output_format must be 'json' or 'jsonl'")

    return output_path


def load_and_save_documents(
    root_dir: str | Path,
    output_file: str | Path,
    patterns: Sequence[str] = ("*.pdf",),
    recursive: bool = True,
    max_files: int | None = None,
    output_format: Literal["json", "jsonl"] = "json",
) -> Path:
    """
    Convenience function to load documents and save them to an output file.
    """
    documents = load_documents(
        root_dir=root_dir,
        patterns=patterns,
        recursive=recursive,
        max_files=max_files,
    )
    return save_loaded_documents(
        documents=documents,
        output_file=output_file,
        output_format=output_format,
    )


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Recursively load documents and export text to JSON/JSONL."
    )
    parser.add_argument("root_dir", help="Root directory containing documents")
    parser.add_argument("output_file", help="Path to output file")
    parser.add_argument(
        "--pattern",
        dest="patterns",
        action="append",
        default=["*.pdf"],
        help="Glob pattern to include (repeatable), e.g. --pattern '*.pdf'",
    )
    parser.add_argument(
        "--non-recursive",
        action="store_true",
        help="Do not search recursively",
    )
    parser.add_argument(
        "--max-files",
        type=int,
        default=None,
        help="Maximum number of most-recent files to process",
    )
    parser.add_argument(
        "--format",
        choices=["json", "jsonl"],
        default="json",
        help="Output format",
    )
    return parser


def main() -> None:
    parser = _build_arg_parser()
    args = parser.parse_args()

    output_path = load_and_save_documents(
        root_dir=args.root_dir,
        output_file=args.output_file,
        patterns=tuple(args.patterns),
        recursive=not args.non_recursive,
        max_files=args.max_files,
        output_format=args.format,
    )
    print(f"Saved extracted documents to: {output_path}")


if __name__ == "__main__":
    main()
