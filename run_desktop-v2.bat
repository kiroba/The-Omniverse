@echo off
TITLE The Omniverse - 1-Click Desktop Launcher
:: Force working directory to the script's actual folder location
cd /d "%~dp0"
echo ==================================================================
echo OMNIVERSE DESKTOP 1-CLICK LAUNCHER (WINDOWS)
echo ==================================================================
echo Starting P2P Mesh Relay Daemon and Desktop Control Panel...
python run_desktop-v2.py || python run_desktop.py
pause
