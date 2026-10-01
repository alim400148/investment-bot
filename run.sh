#!/bin/bash
echo "========================================"
echo " Investment Intelligence Bot"
echo "========================================"
if [ -z "$BOT_TOKEN" ]; then
  echo ""
  echo "[خطا] توکن تنظیم نشده!"
  echo ""
  echo "اول این دستور را بزن:"
  echo "  export BOT_TOKEN='توکن_ربات_از_BotFather'"
  echo ""
  echo "بعد دوباره ./run.sh را اجرا کن."
  exit 1
fi
echo "در حال نصب وابستگی‌ها..."
pip install -r requirements.txt -q
echo ""
echo "ربات در حال اجرا..."
python3 bot.py
