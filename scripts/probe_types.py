"""
probe_types.py
--------------
Asks tarkov.dev what fields each type has. One-off helper for fixing
schema-mismatch errors in pull_tarkov_dev.py.
"""

import json
import urllib.request

API_URL = "https://api.tarkov.dev/graphql"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# Types we need to inspect
TYPES_TO_PROBE = ["Prestige", "Mastering", "Achievement", "ServerStatus", "FleaMarket", "PlayerLevel"]

def probe(type_name):
    query = """
    query Probe($name: String!) {
      __type(name: $name) {
        name
        fields {
          name
          type {
            name kind
            ofType { name kind ofType { name kind } }
          }
        }
      }
    }
    """
    payload = json.dumps({"query": query, "variables": {"name": type_name}}).encode()
    req = urllib.request.Request(
        API_URL, data=payload,
        headers={"Content-Type": "application/json", "User-Agent": UA},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = json.loads(resp.read())

    t = body["data"]["__type"]
    if not t or not t.get("fields"):
        print(f"\n=== {type_name}: NO FIELDS or NOT FOUND ===")
        return
    print(f"\n=== {type_name} ===")
    for f in t["fields"]:
        # Resolve return type name
        tt = f["type"]
        type_name_str = ""
        while tt:
            if tt.get("name"):
                type_name_str = tt["name"]
                break
            tt = tt.get("ofType")
        print(f"  {f['name']:35s} -> {type_name_str}")


def main():
    for tn in TYPES_TO_PROBE:
        try:
            probe(tn)
        except Exception as e:
            print(f"\n!! {tn} failed: {e}")


if __name__ == "__main__":
    main()