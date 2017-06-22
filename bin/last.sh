#! /usr/bin/sh

# script to allow intermediate wtmp cleanup
# when doing clean up, save last -Rx output to ~watchdog/last.log
# watchdog will then pick up the saved data

last $*
#| awk '{ if(NF==11)print $1,$2,$3,$4,$5,$6,$8,$7,$9 else print $1,$2,$3,$4,$5,$6,$8,$7,$9,$13 }'


# lars appel 08.jan.08
