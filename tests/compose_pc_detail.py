# -*- coding: utf-8 -*-
"""组装 PC 详情（sync_item_info.info）：
PC 现有内容的文字前缀 + 大标题 + 10 张长图（URL 复用 PE 详情里已上传的）。
输出 _pc.json 供 HTTP /set-pc 使用。PC 编辑器上限 1000 字（图=1字）。"""
import json
import re
import sys
import io
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
read_out = json.load(io.open(ROOT / "_read_out.json", encoding="utf-8"))["data"]
fields = read_out["fields"]

pe_html = fields.get("info") or ""
pc_html = (json.loads(fields["sync_item_info"]) or {}).get("info") or ""
assert pe_html.count("<img") == 10, "PE 详情应有 10 张图: %d" % pe_html.count("<img")


def editor_len(html):
    text = re.sub(r"<[^>]+>", "", html)
    blocks = len(re.findall(r"<p[ >]", html)) + html.count("<br")
    return len(text) + blocks + html.count("<img")


# PC 前缀 = 第一张图所在 <p> 之前的全部内容（老 9/13 日志图在尾部被切掉）
i_img = pc_html.find("<img")
p_start = pc_html.rfind("<p>", 0, i_img) if i_img >= 0 else -1
assert p_start > 0, "PC 前缀定位失败"
prefix = pc_html[:p_start]
for marker in ("更新日志", "版本更新"):
    m_idx = prefix.rfind(marker)
    if m_idx >= 0:
        mp = prefix.rfind("<p>", 0, m_idx)
        if mp >= 0:
            prefix = prefix[:mp]
        break
assert "<img" not in prefix, "PC 前缀混入图片"

urls = re.findall(r'<img src="([^"]+)"', pe_html)
imgs = "".join('<p><img src="%s"></p>' % u for u in urls)

new_html = (prefix
            + "<p><strong style=\"font-size:18px;\">"
              "📢 26.10.26 更新日志（新增80个附魔，共242个）</strong></p>"
            + imgs)

rep = {
    "prefix_editor_len": editor_len(prefix),
    "pc_old_len": editor_len(pc_html),
    "pc_new_len": editor_len(new_html),
    "pc_new_imgs": new_html.count("<img"),
    "prefix_tail": prefix[-60:],
}
io.open(ROOT / "_pc_report.txt", "w", encoding="utf-8").write(
    json.dumps(rep, ensure_ascii=False, indent=1))
assert rep["pc_new_len"] <= 1000, "PC 编辑器字数超限: %d" % rep["pc_new_len"]
assert rep["pc_new_imgs"] == 10

payload = {"name": read_out["name"], "html": new_html}
io.open(ROOT / "_pc.json", "w", encoding="utf-8").write(
    json.dumps(payload, ensure_ascii=False))
print("PC 组装完成: 前缀%d字 旧%d字 新%d字 图%d张" % (
    rep["prefix_editor_len"], rep["pc_old_len"],
    rep["pc_new_len"], rep["pc_new_imgs"]))
