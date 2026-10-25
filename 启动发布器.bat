@echo off
rem 源码运行（开发用）：无控制台窗口，直接打开发布器界面
cd /d "%~dp0"
start "" pythonw mod_publisher.py
