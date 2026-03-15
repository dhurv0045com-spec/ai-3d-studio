@echo off
title AI 3D Studio - API Test
color 0B
cd /d "%~dp0"
echo ================================================
echo  Testing ALL APIs - this finds exactly what works
echo ================================================
echo.
python test_apis.py
echo.
pause
