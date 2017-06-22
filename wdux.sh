#! /usr/bin/sh

# test script to run watchdog report in batch (at or cron)

cd /home/ukfranke/watchdog/wdux
export PATH=${PATH}:/home/ukfranke/watchdog/bin:/home/ukfranke/watchdog/wdux

# create scanable console log

export boottime=$(gawk '{printf "%-12.0f",systime()-$1}' /proc/uptime)
dmesg | awk  -F\] -v boottime=${boottime} '{a=$1;sub(/\[/,"",a);print strftime("%Y-%m-%d %H:%M:%S",boottime+a),$2,$3,$4}' > /tmp/console.log

if [ -d /ISS/data/DE/app/prod/SYS/PUB ]; then
  wdux.py           2>>../wdux.err
else
  wdux.py -p -l -s  2>>../wdux.err
fi

cd ..

#sleep 60; at -f wdux.sh 0005  2>>wdux.err

# lars appel 30.aug.06 / 23.sep.06
