# -*- coding: utf-8 -*-
"""对真实平台页调试抓取逻辑：昵称/头像/详情HTML。只读不改，不点任何保存。"""
import io
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

PROFILE = Path(__file__).resolve().parent.parent / "dist" / "profile"
LIST_URL = "https://mcdev.webapp.163.com/#/work/list/pe_component"
OUT = Path(__file__).resolve().parent / "real_probe.json"

result = {"logged_in": None, "url": None, "topbar_html": None,
          "profile": None, "detail_html": None, "detail_len": None}

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        str(PROFILE), channel="msedge", headless=True,
        viewport={"width": 1440, "height": 960})
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.goto(LIST_URL, wait_until="domcontentloaded")
    page.wait_for_timeout(4000)
    result["url"] = page.url
    result["logged_in"] = "login" not in page.url

    if result["logged_in"]:
        # 1) 顶栏 注销 周围真实结构（截三层祖先HTML片段）
        try:
            result["topbar_html"] = page.evaluate("""() => {
                const all = [...document.querySelectorAll('body *')];
                const lg = all.find(e => !e.children.length &&
                    (e.textContent || '').trim() === '注销');
                if (!lg) return 'NO_LOGOUT_LEAF';
                let p = lg;
                for (let i = 0; i < 3 && p.parentElement; i++) p = p.parentElement;
                return p.outerHTML.slice(0, 2600);
            }""")
        except Exception as e:
            result["topbar_html"] = "ERR %s" % e

        # 2) 现行 read_profile 逻辑跑一遍
        try:
            result["profile"] = page.evaluate("""() => {
                let name = null, avatar = null;
                const all = [...document.querySelectorAll('body *')];
                const logout = all.find(e => !e.children.length &&
                    (e.textContent || '').trim() === '注销');
                if (logout) {
                    let node = logout.previousElementSibling;
                    for (let i = 0; i < 5 && !name && node; i++) {
                        const t = (node.innerText || '').split('\\n')[0].trim();
                        if (t && t !== '注销' && t.length <= 16) name = t;
                        if (node.previousElementSibling) node = node.previousElementSibling;
                        else node = node.parentElement && node.parentElement.previousElementSibling;
                    }
                    let q = logout.parentElement;
                    for (let i = 0; i < 5 && q && !avatar; i++) {
                        const img = q.querySelector('img');
                        if (img && img.src && img.src.startsWith('http')) avatar = img.src;
                        q = q.parentElement;
                    }
                }
                return {name, avatar};
            }""")
        except Exception as e:
            result["profile"] = "ERR %s" % e

        # 3) 真实详情HTML（进趣味附魔编辑页，只读）
        try:
            row = page.get_by_role("row", name="趣味附魔")
            row.wait_for(state="visible", timeout=15000)
            btn = row.get_by_role("button", name="更新")
            if btn.count() != 1:
                btn = row.get_by_role("button", name="编辑")
            btn.first.click()
            page.wait_for_url(lambda u: "#/pe/edit/" in u, timeout=20000)
            page.wait_for_timeout(3500)
            html = page.evaluate(
                "() => { const e = document.querySelector('.ql-editor');"
                " return e ? e.innerHTML : null; }")
            result["detail_html"] = (html or "")[:4000]
            result["detail_len"] = len(html or "")
        except Exception as e:
            result["detail_html"] = "ERR %s" % e
    ctx.close()

OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
print("logged_in=%s" % result["logged_in"])
print("profile=%r" % result.get("profile"))
print("detail_len=%s" % result.get("detail_len"))
print("saved ->", OUT)
