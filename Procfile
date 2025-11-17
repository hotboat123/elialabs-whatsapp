web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
worker: python send_daily_sales_summary.py --daemon-schedule --at 08:00 --tz America/Santiago



