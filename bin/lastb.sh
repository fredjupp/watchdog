#! /usr/bin/sh

# script to allow intermediate btmp cleanup
# when doing clean up, save lastb -Rx output to ~watchdog/lastb.log
# watchdog will then pick up the saved data

dzdo lastb $* |awk '{print $1,$2,$3,$4,$5,$6,$7}'

#| awk '{print $1,$2,$5,$6,$8,$7 }' 

# lars appel 08.jan.08
