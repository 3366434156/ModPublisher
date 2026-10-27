# -*- coding: utf-8 -*-
"""终态验证：读取平台草稿的完整状态（名称/版本/资源包/纪要/详情图数）。"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import publish_api as PA  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

RIDD = "4686112979926756435"

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        str(Path(__file__).resolve().parent.parent / "dist" / "profile"),
        channel="msedge", headless=True)
    pg = ctx.pages[0] if ctx.pages else ctx.new_page()
    pg.goto("https://mcdev.webapp.163.com/", wait_until="domcontentloaded")
    pg.wait_for_timeout(4000)
    api = PA.Api()
    api.set_context(ctx, page=pg)
    print("登录:", api.user_info()["nickname"], flush=True)
    d = api.detail(RIDD)
    html, key = "", None
    for k in ("pe_game_introduction", "info"):
        v = d.get(k) or ""
        if "<p>" in v or "<img" in v:
            html, key = v, k
            break
    text = re.sub(r"<[^>]+>", "", html)
    blocks = len(re.findall(r"<p[ >]", html)) + html.count("<br")
    print(json.dumps({
        "name": d.get("item_name"),
        "version": d.get("item_version"),
        "res_name": (d.get("res") or [{}])[0].get("res_name"),
        "update_summary_head": (d.get("update_summary") or "")[:50],
        "detail_key": key,
        "detail_imgs": html.count("<img"),
        "editor_len": len(text) + blocks + html.count("<img"),
    }, ensure_ascii=False, indent=1), flush=True)
    ctx.close()
