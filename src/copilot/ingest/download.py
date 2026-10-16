"""Step 1 - download the public corpus into data/raw/.

Usage:
    uv run python -m copilot.ingest.download          # download missing files
    uv run python -m copilot.ingest.download --force  # re-download everything

Writes data/raw/manifest.json recording url, sha256, size and download time per file,
so every chunk we index later can be traced back to an exact source version.
"""

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

import httpx
import yaml

from copilot.config import CONFIG_DIR, RAW_DIR, settings

ECFR_API = "https://www.ecfr.gov/api/versioner/v1"


@dataclass
class Source:
    id: str
    kind: str  # "ecfr" | "pdf"
    url: str
    use: str  # "rag" | "structured"
    topic: str
    filename: str


@dataclass
class ManifestEntry:
    id: str
    kind: str
    use: str
    topic: str
    url: str
    path: str
    sha256: str
    bytes: int
    downloaded_at: str


def ecfr_latest_date(client: httpx.Client, title: int) -> str:
    """eCFR needs an explicit date; use the latest date the title is current to."""
    resp = client.get(f"{ECFR_API}/titles.json")
    resp.raise_for_status()
    for t in resp.json()["titles"]:
        if t["number"] == title:
            return t["up_to_date_as_of"]
    raise ValueError(f"Title {title} not found in eCFR")


def load_sources(client: httpx.Client, config_path: Path) -> list[Source]:
    cfg = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    dates: dict[int, str] = {}
    sources: list[Source] = []

    for item in cfg.get("ecfr", []):
        title, section = int(item["title"]), str(item["section"])
        if title not in dates:
            dates[title] = ecfr_latest_date(client, title)
        part = section.split(".")[0]
        url = f"{ECFR_API}/full/{dates[title]}/title-{title}.xml?part={part}&section={section}"
        sources.append(
            Source(item["id"], "ecfr", url, item["use"], item["topic"], f"{item['id']}.xml")
        )

    for item in cfg.get("pdf", []):
        sources.append(
            Source(item["id"], "pdf", item["url"], item["use"], item["topic"], f"{item['id']}.pdf")
        )

    return sources


def download(client: httpx.Client, src: Source, force: bool) -> ManifestEntry:
    out = RAW_DIR / src.id / src.filename
    if out.exists() and not force:
        print(f"  skip  {src.id} (exists)")
        data = out.read_bytes()
    else:
        resp = client.get(src.url)
        resp.raise_for_status()
        data = resp.content
        expected = b"%PDF" if src.kind == "pdf" else b"<?xml"
        if not data.lstrip().startswith(expected):
            raise ValueError(f"{src.id}: unexpected content (not {expected!r}) from {src.url}")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(data)
        print(f"  ok    {src.id} ({len(data) / 1024:,.0f} KB)")

    return ManifestEntry(
        id=src.id,
        kind=src.kind,
        use=src.use,
        topic=src.topic,
        url=src.url,
        path=out.relative_to(RAW_DIR).as_posix(),
        sha256=hashlib.sha256(data).hexdigest(),
        bytes=len(data),
        downloaded_at=datetime.now(UTC).isoformat(timespec="seconds"),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--force", action="store_true", help="re-download existing files")
    args = parser.parse_args()

    headers = {
        # GS1 rejects non-browser User-Agents; identify ourselves via From instead.
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/130.0 Safari/537.36"
        ),
        "From": settings.corpus_contact,
        "Accept-Encoding": "gzip, deflate",  # eCFR refuses uncompressed responses
    }
    with httpx.Client(headers=headers, timeout=120, follow_redirects=True) as client:
        sources = load_sources(client, CONFIG_DIR / "corpus_sources.yaml")
        print(f"Downloading {len(sources)} sources into {RAW_DIR}")
        entries, failures = [], []
        for src in sources:
            try:
                entries.append(download(client, src, args.force))
            except (httpx.HTTPError, ValueError) as exc:
                print(f"  FAIL  {src.id}: {exc}")
                failures.append(src.id)

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    manifest = RAW_DIR / "manifest.json"
    manifest.write_text(json.dumps([asdict(e) for e in entries], indent=2), encoding="utf-8")
    total_mb = sum(e.bytes for e in entries) / 1e6
    print(f"\n{len(entries)} files, {total_mb:.1f} MB -> {manifest}")
    if failures:
        raise SystemExit(f"Failed: {', '.join(failures)}")


if __name__ == "__main__":
    main()
