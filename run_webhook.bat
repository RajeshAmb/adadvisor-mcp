@echo off
cd /d C:\Users\ambav\meta-ads-manager
python webhook_server.py >> logs\webhook.log 2>&1
