#!/bin/bash
source venv/bin/activate
cd daemon
python2 experiment_handler_daemon.py stop
python2 quality_check_daemon.py stop
python2 server_status_daemon.py stop
cd ..
screen -X -S RAS kill
