"""
pull_item_icons.py
------------------
Reads ../data/latest/items.json and downloads each item's icon
from assets.tarkov.dev into ../icons/from-tarkov-dev/items/.

Skips files that already exist (so re-running only fetches new items).

Run locally:
    cd scripts
    python pull_item_icons.py
"""

import json
import sys
import time
from pathlib import Path
import urllib.request
import urllib.error

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
ITEMS_JSON = REPO_ROOT / "data" / "latest" / "items.json"
OUT_DIR = REPO_ROOT / "icons" / "from-tarkov-dev" / "items"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# Be polite — small delay between requests
DELAY_SECONDS = 0.05      # 50ms between requests = ~20/sec
PROGRESS_EVERY = 100      # print status every N items

# Which image to download. iconLink = small (fastest), gridImageLink = medium, image512pxLink = large
IMAGE_FIELD = "iconLink"


def download_one(url: str, dest: Path) -> bool:
    """Download a single file. Returns True if downloaded, False if failed."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
        dest.write_bytes(data)
        return True
    except (urllib.error.HTTPError, urllib.error.URLError) as e:
        print(f"  X {dest.name}: {e}", flush=True)
        return False
    except Exception as e:
        print(f"  X {dest.name}: unexpected error {e}", flush=True)
        return False


def main():
    if not ITEMS_JSON.exists():
        print(f"X items.json not found at {ITEMS_JSON}", flush=True)
        print("  Run pull_tarkov_dev.py first.", flush=True)
        sys.exit(1)

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Reading items from {ITEMS_JSON}", flush=True)
    items = json.loads(ITEMS_JSON.read_text(encoding="utf-8"))
    print(f"Found {len(items)} items", flush=True)
    print(f"Downloading {IMAGE_FIELD} for each into {OUT_DIR}", flush=True)
    print(f"Existing files are skipped (re-runs only fetch new items).\n", flush=True)

    downloaded = 0
    skipped = 0
    failed = 0
    no_url = 0

    started = time.time()

    for i, item in enumerate(items, 1):
        item_id = item.get("id")
        url = item.get(IMAGE_FIELD)

        if not item_id:
            continue
        if not url:
            no_url += 1
            continue

        # Determine extension from URL
        ext = ".webp"
        url_lower = url.lower()
        if url_lower.endswith(".png"):
            ext = ".png"
        elif url_lower.endswith(".jpg") or url_lower.endswith(".jpeg"):
            ext = ".jpg"

        dest = OUT_DIR / f"{item_id}{ext}"

        if dest.exists() and dest.stat().st_size > 0:
            skipped += 1
        else:
            ok = download_one(url, dest)
            if ok:
                downloaded += 1
                time.sleep(DELAY_SECONDS)
            else:
                failed += 1

        if i % PROGRESS_EVERY == 0:
            elapsed = time.time() - started
            rate = i / elapsed if elapsed > 0 else 0
            remaining = len(items) - i
            eta_sec = remaining / rate if rate > 0 else 0
            print(
                f"  [{i}/{len(items)}] "
                f"new={downloaded} skip={skipped} fail={failed} no-url={no_url} "
                f"({rate:.1f}/s, ETA {eta_sec:.0f}s)",
                flush=True,
            )

    elapsed = time.time() - started
    print(
        f"\nDone in {elapsed:.0f}s. "
        f"Downloaded {downloaded}, skipped {skipped}, "
        f"failed {failed}, no URL {no_url}.",
        flush=True,
    )
    print(f"Icons live in: {OUT_DIR}", flush=True)


if __name__ == "__main__":
    main()