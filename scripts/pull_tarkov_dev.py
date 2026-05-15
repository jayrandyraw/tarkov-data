"""
pull_tarkov_dev.py
------------------
Pulls all structured game data from tarkov.dev's public GraphQL API.
Writes individual JSON files into ../data/latest/.

Covers 22 datasets: traders, tasks, items, hideout, maps, barters, crafts,
ammo, bosses, achievements, prestige, playerLevels, mastering, skills,
questItems, handbookCategories, itemCategories, fleaMarket, armorMaterials,
stationaryWeapons, lootContainers, status.

Skipped (use live-data scripts instead): historicalItemPrices,
archivedItemPrices, itemPrices, goonReports.

Run locally:
    cd scripts
    python pull_tarkov_dev.py
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import urllib.request
import urllib.error

API_URL = "https://api.tarkov.dev/graphql"
LANG = "en"
GAME_MODE = "regular"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
OUT_DIR = REPO_ROOT / "data" / "latest"

# ---------------------------------------------------------------------------
# Queries that accept BOTH lang AND gameMode arguments
# ---------------------------------------------------------------------------
LANG_GAME_QUERIES = {
    "traders": """
        query Traders($lang: LanguageCode, $gameMode: GameMode) {
            traders(lang: $lang, gameMode: $gameMode) {
                id name normalizedName description resetTime
                currency { id name }
                discount
                levels {
                    id level requiredPlayerLevel requiredReputation requiredCommerce
                    payRate insuranceRate repairCostMultiplier
                }
                imageLink image4xLink
            }
        }
    """,
    "tasks": """
        query Tasks($lang: LanguageCode, $gameMode: GameMode) {
            tasks(lang: $lang, gameMode: $gameMode) {
                id name normalizedName
                trader { id name normalizedName }
                map { id name normalizedName }
                experience wikiLink taskImageLink minPlayerLevel
                taskRequirements { task { id name } status }
                traderRequirements { trader { id name } compareMethod value }
                kappaRequired lightkeeperRequired restartable factionName
                objectives {
                    id type description optional
                    maps { id name }
                }
                startRewards {
                    items { item { id name } count }
                    offerUnlock { id trader { id name } level item { id name } }
                    skillLevelReward { name level }
                    traderStanding { trader { id name } standing }
                    traderUnlock { id name }
                }
                finishRewards {
                    items { item { id name } count }
                    offerUnlock { id trader { id name } level item { id name } }
                    skillLevelReward { name level }
                    traderStanding { trader { id name } standing }
                    traderUnlock { id name }
                    craftUnlock { id }
                }
            }
        }
    """,
    "items": """
        query Items($lang: LanguageCode, $gameMode: GameMode) {
            items(lang: $lang, gameMode: $gameMode) {
                id name shortName normalizedName
                basePrice width height weight
                wikiLink iconLink gridImageLink image512pxLink
                types
                avg24hPrice low24hPrice high24hPrice changeLast48hPercent
                lastLowPrice fleaMarketFee
                sellFor { vendor { name } price priceRUB currency }
                buyFor { vendor { name } price priceRUB currency }
                category { id name }
                conflictingItems { id }
            }
        }
    """,
    "hideout": """
        query Hideout($lang: LanguageCode, $gameMode: GameMode) {
            hideoutStations(lang: $lang, gameMode: $gameMode) {
                id name normalizedName imageLink
                levels {
                    id level constructionTime description
                    itemRequirements { item { id name } count }
                    stationLevelRequirements { station { id name } level }
                    skillRequirements { name level }
                    traderRequirements { trader { id name } level }
                    bonuses { name type value passive production }
                    crafts {
                        id duration
                        requiredItems { item { id name } count }
                        rewardItems { item { id name } count }
                    }
                }
            }
        }
    """,
    "maps": """
        query Maps($lang: LanguageCode, $gameMode: GameMode) {
            maps(lang: $lang, gameMode: $gameMode) {
                id name normalizedName wiki description
                enemies raidDuration players
                bosses {
                    name spawnChance
                    spawnLocations { name chance }
                    escorts { name amount { count chance } }
                }
                extracts { id name faction switches { id name } }
                switches { id name }
            }
        }
    """,
    "barters": """
        query Barters($lang: LanguageCode, $gameMode: GameMode) {
            barters(lang: $lang, gameMode: $gameMode) {
                id
                trader { id name }
                level
                taskUnlock { id name }
                requiredItems { item { id name } count }
                rewardItems { item { id name } count }
            }
        }
    """,
    "crafts": """
        query Crafts($lang: LanguageCode, $gameMode: GameMode) {
            crafts(lang: $lang, gameMode: $gameMode) {
                id
                station { id name }
                level duration
                taskUnlock { id name }
                requiredItems { item { id name } count }
                rewardItems { item { id name } count }
            }
        }
    """,
    "ammo": """
        query Ammo($lang: LanguageCode, $gameMode: GameMode) {
            ammo(lang: $lang, gameMode: $gameMode) {
                item { id name shortName iconLink }
                caliber damage armorDamage penetrationPower
                projectileCount fragmentationChance initialSpeed tracer
            }
        }
    """,
    "bosses": """
        query Bosses($lang: LanguageCode, $gameMode: GameMode) {
            bosses(lang: $lang, gameMode: $gameMode) {
                id name normalizedName
                health { id max }
                imagePortraitLink imagePosterLink
                equipment { item { id name } count }
                items { id name }
            }
        }
    """,
    "prestige": """
        query Prestige($lang: LanguageCode, $gameMode: GameMode) {
            prestige(lang: $lang, gameMode: $gameMode) {
                id name prestigeLevel
                imageLink iconLink
                conditions {
                    id type description optional
                    maps { id name }
                }
                rewards {
                    items { item { id name } count }
                    offerUnlock { id trader { id name } level item { id name } }
                    skillLevelReward { name level }
                    traderStanding { trader { id name } standing }
                    traderUnlock { id name }
                }
            }
        }
    """,
    "fleaMarket": """
        query FleaMarket($lang: LanguageCode, $gameMode: GameMode) {
            fleaMarket(lang: $lang, gameMode: $gameMode) {
                name normalizedName
                minPlayerLevel enabled foundInRaidRequired
                sellOfferFeeRate sellRequirementFeeRate
                reputationLevels { offers offersSpecialEditions minRep maxRep }
            }
        }
    """,
}

# ---------------------------------------------------------------------------
# Queries that take only lang (or no args)
# ---------------------------------------------------------------------------
LANG_ONLY_QUERIES = {
    "achievements": """
        query Achievements($lang: LanguageCode) {
            achievements(lang: $lang) {
                id name description hidden
                playersCompletedPercent
                adjustedPlayersCompletedPercent
                side normalizedSide
                rarity normalizedRarity
                imageLink
            }
        }
    """,
    "questItems": """
        query QuestItems($lang: LanguageCode) {
            questItems(lang: $lang) {
                id name shortName normalizedName
                description
                width height
                iconLink gridImageLink image512pxLink
            }
        }
    """,
    "handbookCategories": """
        query HandbookCategories($lang: LanguageCode) {
            handbookCategories(lang: $lang) {
                id name normalizedName
                parent { id name }
                children { id name }
            }
        }
    """,
    "itemCategories": """
        query ItemCategories($lang: LanguageCode) {
            itemCategories(lang: $lang) {
                id name normalizedName
                parent { id name }
                children { id name }
            }
        }
    """,
    "lootContainers": """
        query LootContainers($lang: LanguageCode) {
            lootContainers(lang: $lang) {
                id name normalizedName
            }
        }
    """,
    "stationaryWeapons": """
        query StationaryWeapons($lang: LanguageCode) {
            stationaryWeapons(lang: $lang) {
                id name shortName
            }
        }
    """,
    "armorMaterials": """
        query ArmorMaterials($lang: LanguageCode) {
            armorMaterials(lang: $lang) {
                id name destructibility minRepairDegradation
                maxRepairDegradation explosionDestructibility
                minRepairKitDegradation maxRepairKitDegradation
            }
        }
    """,
    "skills": """
        query Skills($lang: LanguageCode) {
            skills(lang: $lang) { id name }
        }
    """,
    "mastering": """
        query Mastering($lang: LanguageCode) {
            mastering(lang: $lang) {
                id level2 level3
                weapons { id name shortName }
            }
        }
    """,
}

# ---------------------------------------------------------------------------
# Queries that take NO arguments
# ---------------------------------------------------------------------------
NO_ARG_QUERIES = {
    "playerLevels": """
        query PlayerLevels {
            playerLevels { level exp levelBadgeImageLink }
        }
    """,
    "status": """
        query Status {
            status {
                generalStatus { name message status }
                currentStatuses { name message status }
                messages { time type content solveTime }
            }
        }
    """,
}


def run_query(name: str, query: str, kind: str) -> dict:
    """kind: 'lang_game' | 'lang' | 'none'"""
    variables = {}
    if kind == "lang_game":
        variables = {"lang": LANG, "gameMode": GAME_MODE}
    elif kind == "lang":
        variables = {"lang": LANG}

    payload = json.dumps({"query": query, "variables": variables}).encode("utf-8")

    req = urllib.request.Request(
        API_URL,
        data=payload,
        headers={"Content-Type": "application/json", "User-Agent": USER_AGENT},
        method="POST",
    )

    print(f"  -> fetching {name} ...", flush=True)
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        print(f"  X HTTP {e.code} for {name}: {e.reason}", flush=True)
        raise
    except urllib.error.URLError as e:
        print(f"  X Network error for {name}: {e.reason}", flush=True)
        raise

    body = json.loads(raw)
    if "errors" in body and body["errors"]:
        print(f"  ! GraphQL errors for {name}:", flush=True)
        for err in body["errors"]:
            print(f"     - {err.get('message', err)}", flush=True)
    return body.get("data", {})


def main():
    print(f"tarkov.dev mirror -- writing to {OUT_DIR}", flush=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    started_at = datetime.now(timezone.utc)
    results = {}
    failures = []

    all_queries = []
    all_queries += [(n, q, "lang_game") for n, q in LANG_GAME_QUERIES.items()]
    all_queries += [(n, q, "lang") for n, q in LANG_ONLY_QUERIES.items()]
    all_queries += [(n, q, "none") for n, q in NO_ARG_QUERIES.items()]

    for name, query, kind in all_queries:
        try:
            data = run_query(name, query, kind)
            if data:
                first_key = next(iter(data))
                payload = data[first_key]
            else:
                payload = None

            out_file = OUT_DIR / f"{name}.json"
            out_file.write_text(
                json.dumps(payload, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

            count = len(payload) if isinstance(payload, list) else "n/a"
            size_kb = out_file.stat().st_size / 1024
            print(f"  OK {name}: {count} records, {size_kb:.1f} KB", flush=True)
            results[name] = {
                "records": count if isinstance(count, int) else None,
                "kb": round(size_kb, 1),
            }
        except Exception as e:
            print(f"  X {name} FAILED: {e}", flush=True)
            failures.append({"name": name, "error": str(e)})

    finished_at = datetime.now(timezone.utc)

    meta = {
        "snapshot_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "duration_seconds": (finished_at - started_at).total_seconds(),
        "source": API_URL,
        "language": LANG,
        "game_mode": GAME_MODE,
        "queries_attempted": len(all_queries),
        "queries_succeeded": len(results),
        "queries_failed": len(failures),
        "results": results,
        "failures": failures,
    }
    (OUT_DIR / "_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"\n  wrote _meta.json", flush=True)

    if failures:
        print(f"\n! Finished with {len(failures)} failure(s). See _meta.json.", flush=True)
        sys.exit(1)
    else:
        print(f"\nOK All {len(all_queries)} queries succeeded.", flush=True)


if __name__ == "__main__":
    main()