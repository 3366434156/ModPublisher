# -*- coding: utf-8 -*-
"""只读探针：读平台在线详情，打印结构/字数口径/图片数（不写任何东西）。

用途：确认「详情编辑器真实上限」到底是 405 还是更高，以及在线详情当前的组成，
供修正 tests/do_publish.py 与发布基线结论用。
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import publish_api as PA  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

RIDD = "4686112979926756435"
CDP = "http://127.0.0.1:9222"


def editor_len(html):
    """do_publish.py 现行口径：纯文本字符 + 块级数 + 每图 1"""
    text = re.sub(r"<[^>]+>", "", html)
    blocks = len(re.findall(r"<p[ >]", html)) + html.count("<br")
    return len(text) + blocks + html.count("<img")


with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp(CDP, timeout=8000)
    ctx = browser.contexts[0]
    pg = ctx.new_page()
    pg.goto("https://mcdev.webapp.163.com/", wait_until="domcontentloaded")
    pg.wait_for_timeout(3000)
    api = PA.Api()
    api.set_context(ctx, page=pg)
    print("登录:", api.user_info()["nickname"], flush=True)

    d = api.detail(RIDD)
    print("── 作品级字段 ──", flush=True)
    print("  名称:", d.get("item_name"), "| 版本:", d.get("item_version"),
          "| 模组码:", d.get("vanity_number"), flush=True)
    print("  资源包:", (d.get("res") or [{}])[0].get("res_name"), flush=True)
    print("  更新纪要:", len(d.get("update_summary") or ""), "字 |",
          (d.get("update_summary") or "")[:40], flush=True)
    print("  定价档:", d.get("price_rank"), d.get("price"), flush=True)
    for k, v in sorted(d.items()):
        if not re.search(r"status|commit|online|check|review|audit", k, re.I):
            continue
        if isinstance(v, (str, int, float, bool)) or v is None:
            print("  %s = %r" % (k, v), flush=True)
    print("── 详情级字段 ──", flush=True)
    key, html = None, ""
    for k in ("pe_game_introduction", "info"):
        v = d.get(k) or ""
        if "<p>" in v or "<img" in v:
            key, html = k, v
            break
    print("字段:", key, "| HTML长度:", len(html), "| 图片:", html.count("<img"),
          "| editor_len≈", editor_len(html), flush=True)

    imgs = re.findall(r'<img[^>]*src="([^"]+)"', html)
    for i, u in enumerate(imgs, 1):
        print("  图%d: %s" % (i, u), flush=True)

    i_img = html.find("<img")
    p_start = html.rfind("<p>", 0, i_img) if i_img >= 0 else -1
    prefix = html[:p_start] if p_start > 0 else ""
    print("前缀 HTML长度:", len(prefix), "| 前缀 editor_len≈", editor_len(prefix),
          flush=True)
    dump = Path(__file__).resolve().parent / "live_detail_dump.html"
    dump.write_text(html, encoding="utf-8")
    print("已导出在线详情HTML ->", dump, flush=True)
    print("前缀前 300:", prefix[:300].replace("\n", ""), flush=True)
    print("前缀尾 200:", prefix[-200:].replace("\n", ""), flush=True)
    print("图片区前 300:", html[p_start:p_start + 300] if p_start > 0 else "", flush=True)

    # 文本段概览
    for i, t in enumerate(re.findall(r"<p[^>]*>(.*?)</p>", html, re.S), 1):
        clean = re.sub(r"<[^>]+>", "", t).strip()
        print("  p%-2d len=%-4d imgs=%d %s" % (
            i, len(clean), t.count("<img"), clean[:70] or ("[图片x%d]" % t.count("<img"))),
            flush=True)
    try:
        pg.close()
    except Exception:
        pass
