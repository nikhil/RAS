#!/bin/bash
source venv/bin/activate
cd daemon
python2 experiment_handler_daemon.py start
python2 quality_check_daemon.py start
python2 server_status_daemon.py start
cd ..
screen -d -m -S RAS bash -c  'python2 app.py >> server_log.txt 2>&1'