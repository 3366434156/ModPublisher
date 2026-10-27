# -*- coding: utf-8 -*-
"""实测「详情能放几张图 / 多少字」——先备份线上详情，逐档试，最后原样还原。
用法：py -3 probe_img_cap.py
输出：tests/live_cap.log + tests/live_detail_backup.json
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from playwright.sync_api import sync_playwright

import publish_api as PA

ROOT = Path(__file__).resolve().parent.parent
T = Path(__file__).resolve().parent
RIDD = "4686112979926756435"
CDP = "http://127.0.0.1:9222"


def editor_len(html):
    t = re.sub(r"<[^>]+>", "", html)
    return len(t) + len(re.findall(r"<p[ >]", html)) + html.count("<br") \
        + len(re.findall(r"<img", html))


def describe(api):
    d = api.detail(RIDD)
    fld = "info" if "info" in d and ("<" in str(d["info"])) else "pe_game_introduction"
    html = d[fld]
    return d, fld, html


with sync_playwright() as p:
    try:
        browser = p.chromium.connect_over_cdp(CDP, timeout=6000)
        ctx = browser.contexts[0]
        print("附加 9222 OK", flush=True)
    except Exception as e:
        print("附加失败(%s)，用发布器 profile 另起" % e, flush=True)
        ctx = p.chromium.launch_persistent_context(
            str(ROOT / "dist" / "profile"), channel="msedge", headless=True)
    pg = ctx.pages[0] if ctx.pages else ctx.new_page()
    if "mcdev.webapp.163.com" not in (pg.url or ""):
        pg.goto("https://mcdev.webapp.163.com/#/work/list/pe_component",
                wait_until="domcontentloaded")
    pg.wait_for_timeout(1500)

    api = PA.Api()
    api.set_context(ctx, page=pg)
    info = api.user_info()
    print("登录:", json.dumps(info, ensure_ascii=False)[:160], flush=True)

    d, fld, html = describe(api)
    print("当前: 版本 %s | status=%s | %s %d 字符 | %d 图 | 字数 %d" % (
        d.get("version"), d.get("status"), fld, len(html),
        len(re.findall(r"<img", html)), editor_len(html)), flush=True)

    # ---- 备份 ----
    bk = T / "live_detail_backup.json"
    bk.write_text(json.dumps({"version": d.get("version"), "status": d.get("status"),
                              "field": fld, "html": html}, ensure_ascii=False),
                  encoding="utf-8")
    print("已备份 →", bk, flush=True)

    urls = re.findall(r'<img[^>]+src="([^"]+)"', html)
    title = "<p><strong>\U0001F4E226.10.26\u66f4\u65b0</strong></p>"
    # 前缀 = 标题行之前的所有内容
    i = html.find("<p><strong>")
    prefix = html[:i] if i >= 0 else html

    def build(n):
        imgs = "".join('<p><img src="%s"></p>' % urls[k % len(urls)]
                       for k in range(n))
        return prefix + title + imgs

    try:
        for n in (15, 18, 20):
            cand = build(n)
            print("\n=== 试 %d 图（预期字数 %d）" % (n, editor_len(cand)), flush=True)
            try:
                r = api.update_item(RIDD, PA.build_update_body(
                    api.detail(RIDD), {fld: cand}))
                print("  update 返回:", json.dumps(r, ensure_ascii=False)[:200],
                      flush=True)
            except Exception as e:
                print("  update 异常:", str(e)[:300], flush=True)
                continue
            d2, _, h2 = describe(api)
            print("  回读: 版本 %s | %d 字符 | %d 图 | 字数 %d" % (
                d2.get("version"), len(h2), len(re.findall(r"<img", h2)),
                editor_len(h2)), flush=True)
    finally:
        print("\n=== 还原备份 ===", flush=True)
        api.update_item(RIDD, PA.build_update_body(
            api.detail(RIDD), {fld: html}))
        d3, _, h3 = describe(api)
        print("还原后: 版本 %s | %d 图 | 字数 %d | 一致=%s" % (
            d3.get("version"), len(re.findall(r"<img", h3)), editor_len(h3),
            h3 == html), flush=True)

print("=== 完成 ===", flush=True)
