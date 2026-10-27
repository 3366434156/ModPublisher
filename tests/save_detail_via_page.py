# -*- coding: utf-8 -*-
"""经官方编辑页 Quill 保存详情（官方前端保证净化规则）。
先在 API 侧组装好 new_html，再进真页面写入并点 PE详情信息 分块的「更新」。"""
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import publish_core as core  # noqa: E402
import publish_api as PA  # noqa: E402

core.PROFILE_DIR = Path(__file__).resolve().parent.parent / "dist" / "profile"
NAME = "趣味附魔 - 共242个附魔"
RIDD = "4686112979926756435"
NEW_NAME = "趣味附魔 - 共242个附魔"
IMGS = Path(__file__).resolve().parent / "pubimgs"
LOG = Path(__file__).resolve().parent / "publish_result.json"
pub = json.loads(LOG.read_text(encoding="utf-8"))
urls = {k: v for k, v in pub["urls"].items() if k.startswith("90_更新日志")}
ENCHANT_IMGS = sorted((Path(__file__).resolve().parent / "pubimgs").glob("*附魔*.png"))
print("待上传附魔图:", len(ENCHANT_IMGS), flush=True)

cfg = core.load_config()
cfg["headless_browser"] = True
host = mp = __import__("mod_publisher").Host(cfg)
host.start()
S = host.submit

new_html = None
detail = {}

def stage1():
    """停靠页：读 detail + 上传附魔图 + 组装 new_html"""
    global new_html, detail
    for i, f in enumerate(ENCHANT_IMGS, 1):
        info = host.api.upload("image", f, "image/png")
        urls[f.name] = json.loads(info["body"])["url"]
        print("上传附魔图 %d/%d" % (i, len(ENCHANT_IMGS)), flush=True)
    detail = host.api.detail(RIDD)
    old_html = ""
    key = None
    for k in ("pe_game_introduction", "info"):
        v = detail.get(k) or ""
        if "<p>" in v or "<img" in v:
            old_html, key = v, k
            break
    host._detail_key = key
    idx = old_html.find("以下是一些附魔的详细介绍")
    p_start = old_html.rfind("<p>", 0, idx)
    prefix = old_html[:p_start]

    def imgs(pred):
        return "".join('<p><img src="%s"></p>' % urls[n]
                       for n in sorted(urls) if pred(n))
    log_imgs = lambda n: n.startswith("90_更新日志")
    det_imgs = lambda n: "附魔详细介绍" in n or "附魔总览" in n
    new_html = (
        prefix
        + "<p><strong style=\"font-size:18px;\">📢 26.10.26 更新日志（新增80个附魔，共242个）</strong></p>"
        + imgs(log_imgs) + "<p><br></p>"
        + old_html[p_start:old_html.find("</p>", idx) + 4]
        + imgs(det_imgs))
    return {"key": key, "len": len(new_html),
            "imgs": new_html.count("<img")}

info = S(stage1)
print("组装: key=%s len=%d imgs=%d" % (info["key"], info["len"], info["imgs"]), flush=True)


def stage2():
    """真编辑页：Quill 写入 + 点 PE详情信息 分块的「更新」按钮"""
    eng = host.eng
    eng.open_editor(re.escape(NAME), key=NAME)
    page = eng.page
    page.wait_for_timeout(1500)
    r = page.evaluate(
        """(html) => {
        const ed = document.querySelector('.ql-editor');
        if (!ed) return {ok: false, err: '未找到Quill编辑器'};
        ed.innerHTML = html;
        ed.dispatchEvent(new Event('input', {bubbles: true}));
        // 锚点法：含「PE详情信息」的最小元素 → 向上找同时含「更新」按钮的容器
        const all = [...document.querySelectorAll('body *')]
            .filter(e => (e.textContent || '').includes('PE详情信息'));
        const smallest = all.sort((a, b) =>
            a.textContent.length - b.textContent.length)[0];
        let btn = null;
        let c = smallest;
        for (let i = 0; i < 6 && c; i++) {
            c = c.parentElement;
            if (!c) break;
            const b = [...c.querySelectorAll('button')]
                .find(x => (x.textContent || '').trim() === '更新');
            if (b) { btn = b; break; }
        }
        if (!btn) return {ok: false, err: '未找到分块更新按钮'};
        btn.click();
        return {ok: true};
    }""", new_html)
    if not r.get("ok"):
        raise RuntimeError(r.get("err"))
    time.sleep(3)
    return {"saved": True}


print("页面保存:", S(stage2, timeout=180), flush=True)

# 重读验证
def verify():
    d = host.api.detail(RIDD)
    v = d.get(host._detail_key) or ""
    return {"len": len(v), "imgs": v.count("<img"),
            "name": d.get("item_name"), "version": d.get("item_version")}
print("重读验证:", S(verify), flush=True)
host.submit(lambda: host.eng.close())
print("=== 官方编辑器保存路径完成 ===", flush=True)
