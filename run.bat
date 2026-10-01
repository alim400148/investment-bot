@echo off
chcp 65001 >nul
echo ========================================
echo  Investment Intelligence Bot
echo ========================================
if "%BOT_TOKEN%"=="" (
  echo.
  echo [خطا] توکن تنظیم نشده!
  echo.
  echo اول این دستور را بزن:
  echo   set BOT_TOKEN=توکن_ربات_از_BotFather
  echo.
  echo بعد دوباره run.bat را اجرا کن.
  pause
  exit /b 1
)
echo در حال نصب وابستگی‌ها...
pip install -r requirements.txt -q
echo.
echo ربات در حال اجرا...
python bot.py
pause
