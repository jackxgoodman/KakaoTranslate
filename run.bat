@echo off
:: Wrapper called by Task Scheduler.
:: Sets the working directory to the script folder before launching.
cd /d "%~dp0"
python main.py
