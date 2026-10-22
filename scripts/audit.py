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
    assert (("world-nuclear-news.org/articles/" in u and x.get("source")=="World Nuclear News") or ("ans.org/news/" in u and x.get("source")=="ANS Nuclear Newswire") or (x.get("kind")=="report" and x.get("source") in ("Nuclear Innovation Alliance","Breakthrough Institute") and u.startswith("https://"))), "Invalid source attribution: "+u
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
