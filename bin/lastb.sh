#! /usr/bin/sh

# script to allow intermediate btmp cleanup
# when doing clean up, save lastb -Rx output to ~watchdog/lastb.log
# watchdog will then pick up the saved data

if [ -r ~/lastb.log ]; then
  sudo lastb $* && cat ~/lastb.log && mv ~/lastb.log ~/lastb.old
else
  sudo lastb $*
fi

# lars appel 08.jan.08
