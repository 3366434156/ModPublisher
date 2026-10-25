# -*- coding: utf-8 -*-
"""起一个常驻 Host + HTTP API（供 CLI 代理/HTTP 测试），存活 N 秒。"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import publish_core as core  # noqa: E402
import mod_publisher as mp  # noqa: E402

DUR = int(sys.argv[1]) if len(sys.argv) > 1 else 240
core.PROFILE_DIR = Path(__file__).resolve().parent.parent / "dist" / "profile"
cfg = core.load_config()
cfg["headless_browser"] = True
host = mp.Host(cfg)
host.start()
port = host.serve_http(8765)
print("SERVING http://127.0.0.1:%d for %ds" % (port, DUR), flush=True)
t0 = time.time()
while time.time() - t0 < DUR and not host._closed.is_set():
    time.sleep(1)
try:
    host.submit(lambda: host.eng.close(), timeout=10)
except Exception:
    pass
print("DONE", flush=True)
