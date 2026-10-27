# -*- coding: utf-8 -*-
"""产出发布素材（优先附加到发布器已打开的 Edge，不另开浏览器）：
1) 附魔介绍.html（瀑布流+三列）一键截图全部 → zip → 解压 PNG
2) 更新日志.md 渲染为 1000 宽长图（≤4000 自动分页）
输出目录：tests/pubimgs/
用法：py -3 gen_detail_images.py [--log-only]
"""
import re
import sys
import time
import zipfile
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(__file__).resolve().parent / "pubimgs"
CDP = "http://127.0.0.1:9222"      # 发布器 Edge 的固定调试端口
SKIP_ENCHANT = "--log-only" in sys.argv

OUT.mkdir(exist_ok=True)
for f in OUT.glob("*"):
    f.unlink()


def enchant_part(page):
    """附魔介绍.html：瀑布流+三列 → 一键截图全部 → 返回 zip 路径"""
    page.set_viewport_size({"width": 1400, "height": 1000})
    page.goto((ROOT.parent / "MoreEnchantments" / "附魔介绍.html").as_uri(),
              wait_until="domcontentloaded")
    page.wait_for_timeout(2500)
    page.click("#masonryToggleBtn")
    page.wait_for_timeout(400)
    for _ in range(4):
        t = page.evaluate("document.getElementById('layoutText').textContent")
        if t == "三列":
            break
        page.click("#layoutToggleBtn")
        page.wait_for_timeout(300)
    layout = page.evaluate("document.getElementById('layoutText').textContent")
    masonry = page.evaluate(
        "document.querySelector('.enchant-grid').classList.contains('masonry')")
    print("布局: %s | masonry=%s" % (layout, masonry), flush=True)
    assert layout == "三列" and masonry, (layout, masonry)
    with page.expect_download(timeout=600000) as dl:
        page.click("#exportAllBtn")
    t0, txt = time.time(), ""
    while time.time() - t0 < 480:
        try:
            txt = page.evaluate(
                "document.getElementById('exportStatus').textContent")
            if "截图完成" in txt:
                break
        except Exception:
            pass
        time.sleep(2)
    print("导出状态:", txt, "| download:", dl.value.suggested_filename, flush=True)
    zpath = OUT / dl.value.suggested_filename
    dl.value.save_as(str(zpath))
    page.close()
    return zpath


def md2html(text):
    out = []
    in_list = False
    for line in text.splitlines():
        s = line.rstrip()
        if not s.strip():
            if in_list:
                out.append("</ul>")
                in_list = False
            continue
        if s.startswith("# "):
            out.append("<h1>%s</h1>" % s[2:])
        elif s.startswith("## "):
            out.append("<h2>%s</h2>" % s[3:])
        elif s.startswith("### "):
            out.append("<h3>%s</h3>" % s[4:])
        elif s.strip() == "---":
            out.append("<hr>")
        elif s.startswith("- "):
            if not in_list:
                out.append("<ul>")
                in_list = True
            item = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s[2:])
            out.append("<li>%s</li>" % item)
        else:
            if in_list:
                out.append("</ul>")
                in_list = False
            out.append("<p>%s</p>" % re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s))
    if in_list:
        out.append("</ul>")
    return "\n".join(out)


def log_part(page):
    """更新日志.md → 1000 宽长图（≤4000 自动分页）"""
    MD_ROOT = ROOT.parent / "MoreEnchantments"
    md = (MD_ROOT / "更新日志.md").read_text(encoding="utf-8-sig")
    page_html = """<!DOCTYPE html><html><head><meta charset="utf-8"><style>
body{margin:0;background:#fff;font-family:"Microsoft YaHei",sans-serif;
  width:1000px;padding:20px 26px;box-sizing:border-box;color:#222}
h1{font-size:22px;border-bottom:2px solid #5b8cff;padding-bottom:6px;margin:0 0 6px}
h2{font-size:16px;color:#2a56c6;margin:14px 0 6px;border-left:4px solid #5b8cff;
  padding-left:8px}
h3{font-size:14px;margin:10px 0 4px;color:#333}
ul{margin:2px 0 8px 18px}
li{margin:1px 0;font-size:10.5px;line-height:1.5}
p{font-size:10.5px;line-height:1.55;margin:3px 0}
hr{border:0;border-top:1px dashed #c9d4ea;margin:8px 0}
b{color:#111}
</style></head><body>%s</body></html>""" % md2html(md)
    render = OUT / "_log_render.html"
    render.write_text(page_html, encoding="utf-8")
    page.set_viewport_size({"width": 1000, "height": 1000})
    page.goto(render.as_uri(), wait_until="domcontentloaded")
    page.wait_for_timeout(600)
    total = page.evaluate("document.body.scrollHeight")
    print("更新日志渲染高度:", total, flush=True)
    n_pages, y = 0, 0
    while y < total:
        h = min(4000, total - y)
        page.screenshot(
            path=str(OUT / ("90_更新日志_%d.png" % (n_pages + 1))),
            clip={"x": 0, "y": y, "width": 1000, "height": h}, full_page=True)
        n_pages += 1
        y += 4000
    page.close()
    render.unlink()


with sync_playwright() as p:
    attached = False
    try:
        browser = p.chromium.connect_over_cdp(CDP, timeout=5000)
        ctx = browser.contexts[0]
        attached = True
        print("已附加到发布器 Edge（所有操作都在这个已打开的窗口里进行）", flush=True)
    except Exception as e:
        print("附加 9222 失败(%s)，本地另起可见窗口" % e, flush=True)
        ctx = p.chromium.launch_persistent_context(
            str(Path(__file__).resolve().parent / "profile_img"),
            channel="msedge", headless=False, accept_downloads=True,
            viewport={"width": 1400, "height": 1000})

    if not SKIP_ENCHANT:
        zpath = enchant_part(ctx.new_page())
        zipfile.ZipFile(zpath).extractall(OUT)
        print("解压图片 %d 张" % len(sorted(OUT.glob("*.png"))), flush=True)
    log_part(ctx.new_page())

    if not attached:
        ctx.close()
    # attach 模式不关浏览器：窗口是发布器的，保持打开

final = sorted(OUT.glob("*.png"))
print("素材完成：%d 张" % len(final), flush=True)
for f in final:
    print("  ", f.name, flush=True)
