# -*- coding: utf-8 -*-
"""建立按类型分组的语料索引，供调研 Agent 使用。"""
import json, os, re, glob

BASE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.join(BASE, "articles")

idx = json.load(open(os.path.join(BASE, "index.json"), encoding="utf-8"))

# 重新从各归档页取元信息
meta = {}
for f in ["gator_archive.html", "xinxicha_archive.html", "archive.html"]:
    p = os.path.join(BASE, f)
    if not os.path.exists(p):
        continue
    s = open(p, encoding="utf-8", errors="ignore").read()
    for m in re.finditer(
        r'<article class="article-row".*?<time datetime="([^"]+)".*?<a href="([^"]+)".*?<h3[^>]*>(.*?)</h3>\s*(?:<p[^>]*>(.*?)</p>)?',
        s, flags=re.S):
        dt, href, title, desc = m.groups()
        slug = href.strip("/").split("/")[-1]
        tags = re.search(r'<span class="source-tag"[^>]*>(.*?)</span>', m.group(0), flags=re.S)
        mins = re.findall(r'<span[^>]*>(\d+) 分钟</span>', m.group(0))
        meta[slug] = {
            "date": dt[:10],
            "title": re.sub(r"<[^>]+>", "", title).strip(),
            "desc": (re.sub(r"<[^>]+>", "", desc).strip() if desc else ""),
            "kind": (re.sub(r"<[^>]+>", "", tags.group(1)).strip() if tags else ""),
            "mins": int(mins[0]) if mins else 0,
            "url": "https://gator.ronchy2000.top" + href,
        }

# 历史研报
rep = {}
rs = ""
for f in ["reports.html"]:
    p = os.path.join(BASE, f)
    if os.path.exists(p):
        rs = open(p, encoding="utf-8", errors="ignore").read()
for m in re.finditer(r'href="(/reports/[^"]+)"[^>]*>(.*?)</a>', rs, flags=re.S):
    href, title = m.groups()
    title = re.sub(r"<[^>]+>", "", title).strip()
    slug = href.strip("/").split("/")[-1]
    if title and slug not in rep:
        rep[slug] = {"title": title, "url": "https://gator.ronchy2000.top" + href}

items = []
for i in idx:
    slug = i["slug"]
    fp = os.path.join(ART, slug + ".txt")
    if not (i.get("ok") and os.path.exists(fp)):
        continue
    m = meta.get(slug)
    if m:
        items.append({**m, "slug": slug, "file": fp, "type": m["kind"] or "每日复盘"})
    elif slug in rep:
        items.append({"date": "", "title": rep[slug]["title"], "desc": "", "kind": "历史研报",
                      "mins": 0, "url": rep[slug]["url"], "slug": slug, "file": fp, "type": "历史研报"})

# 研报日期：研报正文首行常含日期
for it in items:
    if it["type"] == "历史研报" and not it["date"]:
        try:
            head = open(it["file"], encoding="utf-8").read(1500)
            mm = re.search(r"(20\d{2})[.\-/年](\d{1,2})[.\-/月](\d{1,2})", head)
            if mm:
                it["date"] = f"{mm.group(1)}-{int(mm.group(2)):02d}-{int(mm.group(3)):02d}"
        except Exception:
            pass

json.dump(items, open(os.path.join(BASE, "corpus.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

from collections import Counter
print(Counter(it["type"] for it in items))
print("研报有日期:", sum(1 for it in items if it["type"] == "历史研报" and it["date"]))
print("总条目", len(items))

# 生成分组清单文件
groups = {
    "reports": [it for it in items if it["type"] == "历史研报"],
    "reviews": [it for it in items if it["type"] == "每日复盘"],
    "info": [it for it in items if it["type"] == "每日信息"],
}
for g, lst in groups.items():
    with open(os.path.join(BASE, f"list_{g}.json"), "w", encoding="utf-8") as f:
        json.dump(lst, f, ensure_ascii=False, indent=1)
    print(g, len(lst))

# 研报标题全览（供快速浏览体系）
with open(os.path.join(BASE, "reports_titles.txt"), "w", encoding="utf-8") as f:
    for it in sorted(groups["reports"], key=lambda x: x["title"]):
        f.write(f"{it['date'] or '????'} | {it['title']}\n")
print("reports_titles.txt 已生成")
