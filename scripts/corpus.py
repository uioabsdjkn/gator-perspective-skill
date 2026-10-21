# -*- coding: utf-8 -*-
"""语料检索工具：供调研 Agent 在本地 1643 篇语料上批量检索。

用法:
  python corpus.py titles <reports|reviews> [--limit N] [--grep PAT]
  python corpus.py get <slug1> [slug2 ...]        # 输出全文
  python corpus.py grep <PATTERN> [--type reports|reviews] [--limit N] [--ctx N] [--files-only]
  python corpus.py sample <reports|reviews> <N>   # 随机抽样全文
  python corpus.py find <PATTERN> --list          # 列出含关键词的文章标题
"""
import json, os, re, sys, random, glob

BASE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.join(BASE, "articles")
CORPUS = json.load(open(os.path.join(BASE, "corpus.json"), encoding="utf-8"))
BY_SLUG = {c["slug"]: c for c in CORPUS}


def read(slug):
    p = os.path.join(ART, slug + ".txt")
    if not os.path.exists(p):
        return ""
    return open(p, encoding="utf-8", errors="ignore").read()


def body(slug):
    t = read(slug)
    parts = t.split("\n\n", 1)
    return parts[1] if len(parts) > 1 else t


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    cmd = sys.argv[1]
    args = sys.argv[2:]

    ALIAS = {'reports': '历史研报', 'reviews': '每日复盘', 'info': '每日信息'}

    def opt(flag, default=None):
        if flag in args:
            i = args.index(flag)
            return args[i + 1] if i + 1 < len(args) else True
        return default

    if cmd == "titles":
        typ = opt("--type", "reviews")
        limit = int(opt("--limit", 100))
        pat = opt("--grep")
        lst = [c for c in CORPUS if c["type"] == ALIAS.get(typ, typ)]
        if typ == "all":
            lst = CORPUS
        if pat:
            lst = [c for c in lst if re.search(pat, c["title"] + " " + c.get("desc", ""))]
        for c in lst[:limit]:
            print(f"{c['date'] or '????'} | {c['slug']} | {c['title']}")
        print(f"-- 共 {len(lst)} 条 --")

    elif cmd == "get":
        for slug in args:
            c = BY_SLUG.get(slug)
            print("=" * 70)
            print(f"[{c['date'] if c else '??'}] {c['title'] if c else slug}")
            print(f"URL: {c['url'] if c else ''}")
            print("=" * 70)
            print(body(slug))
            print()

    elif cmd == "grep":
        pat = opt("--pattern") or (args[0] if args and not args[0].startswith("--") else "")
        typ = opt("--type", "all")
        limit = int(opt("--limit", 40))
        ctx = int(opt("--ctx", 2))
        files_only = "--files-only" in args
        rx = re.compile(pat)
        lst = CORPUS if typ == "all" else [c for c in CORPUS if c["type"] == ALIAS.get(typ, typ)]
        hits = 0
        for c in lst:
            t = read(c["slug"])
            if not t:
                continue
            lines = t.split("\n")
            matched = [i for i, L in enumerate(lines) if rx.search(L)]
            if not matched:
                continue
            hits += 1
            print(f"\n### {c['date']} | {c['title']}  (slug: {c['slug']})")
            print(f"URL: {c['url']}")
            if files_only:
                continue
            shown = set()
            for i in matched[:8]:
                for j in range(max(0, i - ctx), min(len(lines), i + ctx + 1)):
                    if j not in shown:
                        shown.add(j)
                        print(("  > " if j == i else "    ") + lines[j][:400])
        print(f"\n-- 命中 {hits} 篇 --")

    elif cmd == "find":
        pat = args[0] if args else ""
        typ = opt("--type", "all")
        rx = re.compile(pat)
        lst = CORPUS if typ == "all" else [c for c in CORPUS if c["type"] == ALIAS.get(typ, typ)]
        n = 0
        for c in lst:
            t = body(c["slug"])
            if rx.search(t):
                print(f"{c['date'] or '????'} | {c['slug']} | {c['title']}")
                n += 1
        print(f"-- 命中 {n} 篇 --")

    elif cmd == "sample":
        typ = args[0]
        n = int(args[1]) if len(args) > 1 else 5
        lst = [c for c in CORPUS if c["type"] == ALIAS.get(typ, typ)]
        random.seed(int(os.environ.get("SEED", 42)))
        for c in random.sample(lst, min(n, len(lst))):
            print("=" * 70)
            print(f"[{c['date']}] {c['title']}  (slug: {c['slug']})")
            print(f"URL: {c['url']}")
            print("=" * 70)
            print(body(c["slug"]))
            print()


if __name__ == "__main__":
    main()
