#! /usr/bin/sh

# script to allow intermediate wtmp cleanup
# when doing clean up, save last -Rx output to ~watchdog/last.log
# watchdog will then pick up the saved data

if [ -r ~/last.log ]; then
  last $* && cat ~/last.log && mv ~/last.log ~/last.old
else
  last $*
fi

# lars appel 08.jan.08
