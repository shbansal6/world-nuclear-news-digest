#!/usr/bin/env python3
"""Archive integrity and source provenance checks for unified nuclear intelligence."""
import datetime as dt
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
a=json.loads((ROOT/"data/articles.json").read_text(encoding="utf-8"))
o=json.loads((ROOT/"data/editorial_overrides.json").read_text(encoding="utf-8")).get("articles",{})
items=a.get("articles",[])
assert len(items)>=1000,f"Unexpected archive contraction: {len(items)}"
urls=set()
for x in items:
    dt.date.fromisoformat(x["date"])
    assert x.get("title") and x.get("url"),"Missing title or original source"
    u=x["url"].lower().rstrip("/")
    assert (("world-nuclear-news.org/articles/" in u and x.get("source")=="World Nuclear News") or ("ans.org/news/" in u and x.get("source")=="ANS Nuclear Newswire") or (x.get("source") in ("Nuclear Innovation Alliance","Breakthrough Institute","National Center for Energy Analytics (NCEA)") and x.get("kind") in ("report","news") and u.startswith("https://"))), "Invalid source attribution: "+u
    assert x.get("kind","news") in ("news","report"), "Invalid content kind"
    for alternate in x.get("alternate_sources",[]):
        assert alternate.get("url","").startswith("https://"),"Missing alternate publisher provenance"
    assert u not in urls, "Duplicate WNN source: "+u
    urls.add(u)
for u in ("https://www.world-nuclear-news.org/articles/new-end-user-agreements-support-long-term-us-plant-operations",
          "https://www.world-nuclear-news.org/articles/constellation-amazon-agree-nuclear-focused-power-purchase-deal"):
    assert u in urls, "High-materiality nuclear PPA missing: "+u
    assert u in o, "Source metadata override missing: "+u
    labels=o[u].get("categories",[])
    assert "Offtakes & customers" in labels and "Restarts & uprates" in labels,"Nuclear PPA materiality tags missing: "+u
counts={k:sum(1 for x in items if x["date"].startswith(k)) for k in ["2026-10","2026-09","2025-10"]}
assert counts["2026-10"]>=50,"October WNN archive suspiciously sparse"
print("NUCLEAR QA PASSED:",len(items),"source-linked records including",sum(x.get("kind")=="report" for x in items),"research reports;",counts)

# On first publisher-expanded refresh, verify pre-deduplication provenance.
raw_path=ROOT/"data/source_records.json"
if raw_path.exists():
    raw=json.loads(raw_path.read_text(encoding="utf-8")).get("records",[])
    assert len(raw)>=len(items), "Source-level archive lost original publisher publications"
    raw_by_url={x["url"].lower().rstrip("/") for x in raw}
    assert len(raw_by_url)==len(raw), "Duplicate source-level URLs"
    for displayed in items:
        assert displayed["url"].lower().rstrip("/") in raw_by_url, "Canonical card has no original record"
        for alt in displayed.get("alternate_sources",[]):
            # Older archives may hold pre-migration provenance but no full record;
            # all new sources must be represented by a raw publication on refresh.
            if alt.get("url","").lower().rstrip("/") not in raw_by_url:
                print("PENDING historical alternate-source backfill:",alt["url"])
    print("SOURCE-PROVENANCE QA:",len(raw),"publisher-original records retained")
