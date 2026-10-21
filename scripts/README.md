# 语料复现说明

语料源：https://gator.ronchy2000.top/archive/ （1643 篇，2023-07-22 ~ 2026-10-21）

```bash
PY="python3"

"$PY" scrape.py        # 全量抓取 → articles/*.txt + index.json（约 90 秒，6 线程）
"$PY" build_index.py   # 建索引 → corpus.json / list_*.json / reports_titles.txt
"$PY" corpus.py grep "护盘" --type reviews --limit 20 --ctx 2   # 检索
"$PY" corpus.py get <slug>                                     # 取全文
```

抓取器已支持断点续抓（已存在的 .txt 会跳过）。语料本身不随 Skill 分发（体积约 474 万字符），需要时重跑 `scrape.py` 即可。
