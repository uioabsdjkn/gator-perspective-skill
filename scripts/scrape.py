# -*- coding: utf-8 -*-
"""全量抓取鳄鱼派投资档案站点文章，落盘为 JSONL + 纯文本。"""
import re, html, json, os, sys, time, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor

BASE = "https://gator.ronchy2000.top"
OUT = os.path.dirname(os.path.abspath(__file__))
ART_DIR = os.path.join(OUT, "articles")
os.makedirs(ART_DIR, exist_ok=True)

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"


def fetch(url, timeout=40):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="ignore")


def strip_html(s):
    s = re.sub(r"<script.*?</script>", " ", s, flags=re.S | re.I)
    s = re.sub(r"<style.*?</style>", " ", s, flags=re.S | re.I)
    s = re.sub(r"<!--.*?-->", " ", s, flags=re.S)
    s = re.sub(r"<br\s*/?>", "\n", s, flags=re.I)
    s = re.sub(r"</(p|div|li|h[1-6]|tr|section|blockquote)>", "\n", s, flags=re.I)
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s)
    s = re.sub(r"[ \t\u3000]+", " ", s)
    s = re.sub(r"\n\s*\n\s*\n+", "\n\n", s)
    return s.strip()


def parse_archive(path_html):
    """从归档页提取文章条目列表。"""
    items = []
    # article-row 结构
    for m in re.finditer(
        r'<article class="article-row".*?<time datetime="([^"]+)".*?<a href="([^"]+)".*?<h3[^>]*>(.*?)</h3>\s*(?:<p[^>]*>(.*?)</p>)?',
        path_html, flags=re.S):
        dt, href, title, desc = m.groups()
        tags = re.search(r'<span class="source-tag"[^>]*>(.*?)</span>', m.group(0), flags=re.S)
        mins = re.findall(r'<span[^>]*>(\d+) 分钟</span>', m.group(0))
        items.append({
            "date": dt[:10],
            "url": BASE + href,
            "slug": href.strip("/").split("/")[-1],
            "title": strip_html(title),
            "desc": strip_html(desc) if desc else "",
            "kind": strip_html(tags.group(1)) if tags else "",
            "mins": int(mins[0]) if mins else 0,
        })
    return items


def parse_reports(path_html):
    """历史研报页结构不同，单独解析。"""
    items = []
    for m in re.finditer(r'href="(/reports/[^"]+)"[^>]*>(.*?)</a>', path_html, flags=re.S):
        href, title = m.groups()
        title = strip_html(title)
        if not title or title in ("返回", "历史研报"):
            continue
        items.append({"url": BASE + href, "slug": href.strip("/").split("/")[-1], "title": title})
    return items


def body_of(page_html):
    """抽取文章正文主体（去掉导航/页脚）。"""
    m = re.search(r'<article[^>]*>(.*?)</article>', page_html, flags=re.S)
    seg = m.group(1) if m else page_html
    t = strip_html(seg)
    # 去掉站点噪声
    for marker in ["END OF ARTICLE", "已经是最新文章"]:
        if marker in t:
            t = t.split(marker)[0]
    for noise in ["END OF ARTICLE", "原文版权归作者所有", "查看微信原文", "关闭 ×", "累计访客", "累计浏览",
                  "启用 JavaScript", "内容仅供信息交流", "全文检索", "查找信息", "ESC", "全部 ", "每日信息 ",
                  "每日复盘 ", "历史研报 ", "投资随笔 ", "关闭"]:
        if noise in t:
            t = t.split(noise)[0]
    return t.strip()


def main():
    all_items = []
    seen = set()
    for slug in ["archive", "archive/like-a-gator", "archive/huode-xinxicha"]:
        try:
            h = fetch(f"{BASE}/{slug}/")
            got = parse_archive(h)
            print(f"[archive] {slug}: {len(got)} 条", flush=True)
            for it in got:
                if it["url"] not in seen:
                    seen.add(it["url"])
                    all_items.append(it)
        except Exception as e:
            print(f"[archive] {slug} 失败: {e}", flush=True)

    # 历史研报
    try:
        h = fetch(f"{BASE}/reports/")
        reps = parse_reports(h)
        print(f"[reports]: {len(reps)} 条", flush=True)
        for it in reps:
            if it["url"] not in seen:
                seen.add(it["url"])
                it.update({"date": "", "desc": "", "kind": "历史研报", "mins": 0})
                all_items.append(it)
    except Exception as e:
        print(f"[reports] 失败: {e}", flush=True)

    print(f"总计 {len(all_items)} 个 URL 待抓", flush=True)
    with open(os.path.join(OUT, "_url_list.json"), "w", encoding="utf-8") as f:
        json.dump(all_items, f, ensure_ascii=False, indent=1)

    results = []
    done = [0]

    def work(it):
        err = ""
        for attempt in range(3):
            try:
                target = os.path.join(ART_DIR, it["slug"] + ".txt")
                if os.path.exists(target) and os.path.getsize(target) > 200:
                    it["ok"] = True
                    it["chars"] = os.path.getsize(target)
                    done[0] += 1
                    return it
                h = fetch(it["url"])
                txt = body_of(h)
                if len(txt) < 80:
                    raise ValueError(f"正文过短 {len(txt)}")
                with open(os.path.join(ART_DIR, it["slug"] + ".txt"), "w", encoding="utf-8") as f:
                    f.write(f"# {it['title']}\n# 来源: {it['url']}\n# 日期: {it['date']} | 类型: {it['kind']}\n\n{txt}\n")
                it["chars"] = len(txt)
                it["ok"] = True
                done[0] += 1
                if done[0] % 50 == 0:
                    print(f"  已抓 {done[0]}/{len(all_items)}", flush=True)
                return it
            except Exception as e:
                err = str(e)
                time.sleep(1.5 * (attempt + 1))
        it["ok"] = False
        it["err"] = err
        done[0] += 1
        return it

    with ThreadPoolExecutor(max_workers=6) as ex:
        for r in ex.map(work, all_items):
            results.append(r)

    ok = [r for r in results if r.get("ok")]
    print(f"\n抓取完成: 成功 {len(ok)} / {len(results)}")
    with open(os.path.join(OUT, "index.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
