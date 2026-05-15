"""
introspect_schema.py
--------------------
Asks tarkov.dev's GraphQL API what queries are available and writes
the result to ../data/latest/_schema.json.

Use this to discover what data we're NOT yet pulling.
"""

import json
import urllib.request
from pathlib import Path

API_URL = "https://api.tarkov.dev/graphql"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
OUT_FILE = REPO_ROOT / "data" / "latest" / "_schema.json"

# Standard GraphQL introspection query — lists every queryable field
INTROSPECTION = """
{
  __schema {
    queryType {
      fields {
        name
        description
        args {
          name
          type {
            name
            kind
            ofType { name kind }
          }
        }
        type {
          name
          kind
          ofType {
            name
            kind
            ofType { name kind }
          }
        }
      }
    }
  }
}
"""


def main():
    payload = json.dumps({"query": INTROSPECTION}).encode()
    req = urllib.request.Request(
        API_URL,
        data=payload,
        headers={"Content-Type": "application/json", "User-Agent": USER_AGENT},
        method="POST",
    )

    print("Querying tarkov.dev schema...", flush=True)
    with urllib.request.urlopen(req, timeout=60) as resp:
        body = json.loads(resp.read())

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(json.dumps(body, indent=2), encoding="utf-8")

    fields = body["data"]["__schema"]["queryType"]["fields"]
    print(f"\nFound {len(fields)} top-level queries on tarkov.dev:\n", flush=True)

    for f in sorted(fields, key=lambda x: x["name"]):
        # Resolve the return type, walking through NON_NULL/LIST wrappers
        t = f["type"]
        type_name = ""
        is_list = False
        while t:
            if t.get("kind") == "LIST":
                is_list = True
            if t.get("name"):
                type_name = t["name"]
                break
            t = t.get("ofType")
        suffix = "[]" if is_list else ""
        desc = (f.get("description") or "").split("\n")[0].strip()
        print(f"  {f['name']:35s} -> {type_name}{suffix}    {desc[:60]}", flush=True)

    print(f"\nFull schema written to: {OUT_FILE}", flush=True)


if __name__ == "__main__":
    main()