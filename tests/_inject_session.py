# -*- coding: utf-8 -*-
"""把 dist/profile 里的登录 cookie 转移到发布器正在运行的 Edge（9222）。
只读取 cookie 罐、不发起任何鉴权请求，避免票据轮换竞态。"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

DIST = Path(__file__).resolve().parent.parent / "dist" / "profile"
CDP = "http://127.0.0.1:9222"

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        str(DIST), channel="msedge", headless=True)
    cookies = ctx.cookies()
    ctx.close()
print("dist/profile cookie 数:", len(cookies), flush=True)

with sync_playwright() as p:
    b = p.chromium.connect_over_cdp(CDP, timeout=8000)
    c = b.contexts[0]
    c.add_cookies(cookies)
    print("已注入发布器 Edge", flush=True)
print("OK", flush=True)
