@echo off
:: Wrapper called by Task Scheduler.
:: Starts the version set by AUTOSTART_VERSION in config.py / config_local.py.
cd /d "%~dp0"
python start.py
