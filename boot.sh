#!/bin/bash
source venv/bin/activate

while true; do
    echo Waiting for database...
    flask db upgrade
    if [[ "$?" == "0" ]]; then
        break
    fi
    echo Upgrade command failed, retrying in 5 secs...
    sleep 5
done
exec flask run