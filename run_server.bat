@echo off
title InternHunter 24/7 Agent
cd /d "D:\internhunter"
:loop
echo [%date% %time%] Starting InternHunter Agent...
set PORT=8090
"C:\Users\vinay\AppData\Local\Programs\Python\Python310\python.exe" main.py
echo [%date% %time%] InternHunter exited or crashed. Restarting in 5 seconds...
timeout /t 5
goto loop
