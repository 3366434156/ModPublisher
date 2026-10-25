# -*- coding: utf-8 -*-
"""挖顶栏真实DOM：任何包含'注销'文本的最小元素及其容器结构。只读。"""
import io
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

PROFILE = Path(__file__).resolve().parent.parent / "dist" / "profile"
LIST_URL = "https://mcdev.webapp.163.com/#/work/list/pe_component"
OUT = Path(__file__).resolve().parent / "topbar_dom.json"

res = {}
with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        str(PROFILE), channel="msedge", headless=True)
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.goto(LIST_URL, wait_until="domcontentloaded")
    page.wait_for_timeout(4000)
    res["dump"] = page.evaluate("""() => {
        // 找包含'注销'的最小元素
        const all = [...document.querySelectorAll('body *')].filter(e =>
            (e.textContent || '').includes('注销'));
        const smallest = all.slice().sort((a, b) =>
            a.textContent.length - b.textContent.length)[0] || null;
        if (!smallest) return {found: false};
        let c = smallest;
        for (let i = 0; i < 3 && c.parentElement; i++) c = c.parentElement;
        return {
            found: true,
            smallest_tag: smallest.tagName,
            smallest_cls: smallest.className,
            container_html: c.outerHTML.slice(0, 3000)
        };
    }""")
    # 用真实结构验证候选提取器
    res["extract"] = page.evaluate("""() => {
        const all = [...document.querySelectorAll('body *')].filter(e =>
            (e.textContent || '').includes('注销'));
        const smallest = all.slice().sort((a, b) =>
            a.textContent.length - b.textContent.length)[0] || null;
        if (!smallest) return null;
        let name = null, avatar = null;
        // 策略：向上找容器，取其中'注销'前最近的短文本叶子 与 img
        let c = smallest;
        for (let lvl = 0; lvl < 6 && !name; lvl++) {
            c = c.parentElement;
            if (!c) break;
            const leaves = [...c.querySelectorAll('*')].filter(e => {
                if (e.children.length) return false;
                const t = (e.textContent || '').trim();
                return t && t.length >= 2 && t.length <= 16 &&
                    !['注销','系统消息','公告','下载「手机版测试工具」'].includes(t);
            });
            // 文档序在注销元素之前的最后一个叶子
            const before = leaves.filter(e => {
                try { return e.compareDocumentPosition(smallest) & 4; } catch (_) { return false; }
            });
            if (before.length) name = before[before.length - 1].textContent.trim();
            if (!avatar) {
                const img = c.querySelector('img');
                if (img && img.src && img.src.startsWith('http')) avatar = img.src;
            }
        }
        return {name, avatar};
    }""")
    ctx.close()

OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(res.get("extract"), ensure_ascii=False))
print("container head:", (res["dump"].get("container_html") or "")[:400])
