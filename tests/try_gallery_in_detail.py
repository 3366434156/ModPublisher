# -*- coding: utf-8 -*-
"""实验：图鉴长图能否进详情（编辑器字数口径：图=1字，上限约1350字）。
策略：大标题换超短标题腾字数 → 前缀 + 超短标题 + 2日志 + 8图鉴 → 保存 → 重读。
截断则逐级回退：去标题重试 → 恢复已知良好状态（前缀+原标题+2日志）。"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import publish_api as PA  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

RIDD = "4686112979926756435"
IMGS = Path(__file__).resolve().parent / "pubimgs"
CDP = "http://127.0.0.1:9222"


def editor_len(html):
    """近似编辑器字数：文本字符 + 块级换行 + 每张图 1（Quill 图片占 1 字符）"""
    text = re.sub(r"<[^>]+>", "", html)
    blocks = len(re.findall(r"<p[ >]", html)) + html.count("<br")
    return len(text) + blocks + html.count("<img")


GOOD_BANNER = ("<p><strong style=\"font-size:18px;\">"
               "📢 26.10.26 更新日志（新增80个附魔，共242个）</strong></p>")

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp(CDP, timeout=8000)
    ctx = browser.contexts[0]
    print("已附加到发布器 Edge", flush=True)
    pg = ctx.new_page()
    pg.goto("https://mcdev.webapp.163.com/", wait_until="domcontentloaded")
    pg.wait_for_timeout(4000)
    api = PA.Api()
    api.set_context(ctx, page=pg)
    print("登录:", api.user_info()["nickname"], flush=True)

    detail = api.detail(RIDD)
    old_html, key = "", None
    for k in ("pe_game_introduction", "info"):
        v = detail.get(k) or ""
        if "<p>" in v or "<img" in v:
            old_html, key = v, k
            break
    i_img = old_html.find("<img")
    p_start = old_html.rfind("<p>", 0, i_img)
    prefix = old_html[:p_start]
    m_idx = prefix.rfind("更新日志")
    if m_idx >= 0:
        mp = prefix.rfind("<p>", 0, m_idx)
        if mp >= 0:
            prefix = prefix[:mp]
    assert "<img" not in prefix, "前缀混入图片"
    print("前缀 editor_len≈%d" % editor_len(prefix), flush=True)

    def up(name):
        info = api.upload("image", IMGS / name, "image/png")
        return json.loads(info["body"])["url"]

    log_imgs = sorted(f.name for f in IMGS.glob("90_更新日志_*.png"))
    gal_imgs = sorted(f.name for f in IMGS.glob("*_附魔详细介绍*.png"))
    assert len(log_imgs) + len(gal_imgs) <= 10, "平台图片上限 10 张"
    urls = {}
    for i, n in enumerate(log_imgs + gal_imgs, 1):
        urls[n] = up(n)
        print("上传 %d/%d %s" % (i, len(urls), n), flush=True)

    def img_block(names):
        return "".join('<p><img src="%s"></p>' % urls[n] for n in names)

    def save_and_check(html, tag):
        try:
            api.update_item(RIDD, PA.build_update_body(detail, {key: html}))
        except Exception as e:
            print("[%s] 保存被拒: %s" % (tag, str(e)[:120]), flush=True)
            return -1
        d2 = api.detail(RIDD)
        h2 = d2.get(key) or ""
        got = h2.count("<img")
        print("[%s] 回读: editor_len≈%d HTML=%d 图片=%d" % (
            tag, editor_len(h2), len(h2), got), flush=True)
        return got

    # 尝试 1：超短标题 + 2日志 + 8图鉴
    body = (prefix + "<p><strong>📢26.10.26更新</strong></p>"
            + img_block(log_imgs) + img_block(gal_imgs))
    print("尝试1 预计 editor_len≈%d（当前在线版≈%d）" % (
        editor_len(body), editor_len(old_html)), flush=True)
    got = save_and_check(body, "尝试1")

    if got < len(log_imgs) + len(gal_imgs):
        # 尝试 2：完全去标题
        body = prefix + img_block(log_imgs) + img_block(gal_imgs)
        print("尝试2（去标题）预计 editor_len≈%d" % editor_len(body), flush=True)
        got = save_and_check(body, "尝试2")

    if got < len(log_imgs) + len(gal_imgs):
        print("仍截断，回退已知良好状态…", flush=True)
        got = save_and_check(prefix + GOOD_BANNER + img_block(log_imgs), "回退")
        print("=== 结论：编辑器字数上限卡死，图鉴进不了详情 ===", flush=True)
    else:
        print("=== ✓ 全部 %d 张图完整进详情（2日志+8图鉴）===" % got, flush=True)

    try:
        pg.close()
    except Exception:
        pass
