# -*- coding: utf-8 -*-
"""只读探针：在平台前端 JS 里找「详情」相关的字数/图片数量限制常量。
不改平台任何数据。输出 tests/live_limits.log
"""
import json
import re
import sys
from playwright.sync_api import sync_playwright

CDP = "http://127.0.0.1:9222"
KEYS = ["最多", "张图片", "字符", "字数", "详情", "介绍", "imgLimit", "maxImg",
        "contentLimit", "detailLimit", "图片数", "上限"]

JS = r"""
async () => {
  const urls = [];
  for (const e of performance.getEntriesByType('resource')) {
    if (/\.js(\?|$)/.test(e.name)) urls.push(e.name);
  }
  const hits = [];
  for (const u of urls) {
    let t = "";
    try { const r = await fetch(u); t = await r.text(); } catch (e) { continue; }
    if (t.length < 1000) continue;
    for (const k of __KEYS__) {
      let i = -1, n = 0;
      while ((i = t.indexOf(k, i + 1)) >= 0 && n < 4) {
        n++;
        hits.push({file: u.split('/').pop(), key: k,
                   snippet: t.slice(Math.max(0, i - 90), i + 90).replace(/\s+/g, ' ')});
      }
    }
  }
  return hits;
}
"""

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp(CDP, timeout=8000)
    ctx = browser.contexts[0]
    page = None
    for pg in ctx.pages:
        if "mcdev.webapp.163.com" in (pg.url or ""):
            page = pg
            break
    if page is None:
        page = ctx.new_page()
        page.goto("https://mcdev.webapp.163.com/#/work/list/pe_component",
                  wait_until="domcontentloaded")
    page.wait_for_timeout(3000)
    print("页面:", page.url, flush=True)
    script = JS.replace("__KEYS__", json.dumps(KEYS))
    hits = page.evaluate(script)
    print("JS 资源命中:", len(hits), flush=True)
    seen = set()
    for h in hits:
        s = h["snippet"]
        if s in seen:
            continue
        seen.add(s)
        print("\n[%s] key=%s\n  %s" % (h["file"], h["key"], s), flush=True)
    json.dump(hits, open("tests/live_limits.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
print("\n=== 完成 ===", flush=True)
