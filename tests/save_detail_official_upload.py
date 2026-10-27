# -*- coding: utf-8 -*-
"""详情图片全部经官方编辑器上传链路插入（官方转存URL合规），再分块保存。
结构：prefix(现详情净化版前段) + 更新日志标题行 + [官方上传]日志图×2
      + 锚行 + [官方上传]图鉴图×8 → 点「PE详情信息·更新」"""
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import publish_core as core  # noqa: E402
import mod_publisher as mp  # noqa: E402

core.PROFILE_DIR = Path(__file__).resolve().parent.parent / "dist" / "profile"
NAME = "趣味附魔 - 共242个附魔"
RIDD = "4686112979926756435"
IMGS = Path(__file__).resolve().parent / "pubimgs"
LOG = Path(__file__).resolve().parent / "publish_result.json"

# 顺序：更新日志2 → 附魔详细介绍8（官方编辑器 append 到文末=文档顺序）
order = (sorted(IMGS.glob("90_更新日志_*.png"))
         + sorted(IMGS.glob("*_附魔详细介绍.png")))
print("待官方上传图片:", len(order), flush=True)
assert len(order) == 10, [f.name for f in order]

cfg = core.load_config()
cfg["headless_browser"] = True
host = mp.Host(cfg)
host.start()
S = host.submit

prefix = {}

def stage_prefix():
    """读详情，取净化版前段（锚行之前）+ 标题行 + 锚行（无图）"""
    detail = host.api.detail(RIDD)
    old = ""
    for k in ("pe_game_introduction", "info"):
        v = detail.get(k) or ""
        if "<p>" in v or "<img" in v:
            old, host._detail_key = v, k
            break
    idx = old.find("以下是一些附魔的详细介绍")
    if idx < 0:
        raise RuntimeError("锚点缺失")
    p_start = old.rfind("<p>", 0, idx)
    # 前段去图（图片全部改由官方上传插入，避免混合URL被净化）
    head = old[:p_start]
    head = re.sub(r"<p><img[^>]*></p>", "", head)
    anchor = old[p_start:old.find("</p>", idx) + 4]
    prefix["html"] = (head
                      + "<p><strong style=\"font-size:18px;\">"
                        "📢 26.10.26 更新日志（新增80个附魔，共242个）</strong></p><p><br></p>"
                      + anchor)
    return {"prefix_len": len(prefix["html"])}

print("前段:", S(stage_prefix), flush=True)


def stage_editor():
    eng = host.eng
    eng.open_editor(re.escape(NAME), key=NAME)
    page = eng.page
    page.wait_for_timeout(1500)
    # 1) 写入前段（无图）
    r = page.evaluate(
        """(html) => {
        const ed = document.querySelector('.ql-editor');
        if (!ed) return {ok: false, err: '未找到Quill'};
        ed.innerHTML = html;
        ed.dispatchEvent(new Event('input', {bubbles: true}));
        return {ok: true};
    }""", prefix["html"])
    if not r.get("ok"):
        raise RuntimeError(r["err"])
    # 2) 定位官方图片上传 input（详情编辑器自带）
    marked = page.evaluate(
        """() => {
        const quills = [...document.querySelectorAll('.edit-quill')];
        for (const q of quills) {
            let seg = q;
            for (let i = 0; i < 8 && seg; i++) {
                if ((seg.textContent || '').includes('PE详情信息')) {
                    const inp = q.querySelector('input[type=file]');
                    if (inp) { inp.setAttribute('data-detail-img', '1'); return true; }
                }
                seg = seg.parentElement;
            }
        }
        const any = document.querySelector('.edit-quill input[type=file]');
        if (any) { any.setAttribute('data-detail-img', '1'); return true; }
        return false;
    }""")
    if not marked:
        raise RuntimeError("未找到官方详情图片上传控件")
    return {"ok": True}


print("编辑页就绪:", S(stage_editor, timeout=180), flush=True)

# 3) 逐张官方上传（append 到文末）
for i, f in enumerate(order, 1):
    print("官方上传 %d/%d %s" % (i, len(order), f.name), flush=True)
    S(lambda f=f: host.eng.upload_detail_image(NAME, str(f)),
      timeout=180)
print("全部插入完成", flush=True)

# 4) 点 PE详情信息 分块更新
def save_block():
    page = host.eng.page
    r = page.evaluate(
        """() => {
        const all = [...document.querySelectorAll('body *')]
            .filter(e => (e.textContent || '').includes('PE详情信息'));
        const smallest = all.sort((a, b) =>
            a.textContent.length - b.textContent.length)[0];
        let c = smallest;
        for (let i = 0; i < 6 && c; i++) {
            c = c.parentElement;
            if (!c) break;
            const b = [...c.querySelectorAll('button')]
                .find(x => (x.textContent || '').trim() === '更新');
            if (b) { b.click(); return {ok: true}; }
        }
        return {ok: false, err: '未找到分块更新按钮'};
    }""")
    if not r.get("ok"):
        raise RuntimeError(r["err"])
    time.sleep(3)
    return {"saved": True}


print("分块保存:", S(save_block, timeout=120), flush=True)


def verify():
    d = host.api.detail(RIDD)
    v = d.get(host._detail_key) or ""
    return {"len": len(v), "imgs": v.count("<img"),
            "fp_domain": v.count("fp.ps.netease.com"),
            "gph_domain": v.count("gph.netease.com")}


print("重读验证:", S(verify), flush=True)
host.submit(lambda: host.eng.close())
print("=== 官方上传链路完成 ===", flush=True)
