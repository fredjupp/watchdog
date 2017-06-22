#!/usr/bin/python
# -*- coding: iso-8859-1 -*-
''' WatchDog UX module
    
    module name: scan_last.py
    purpose    : get last/lastb output from system (user logons)
    created    : 2006-08-17
    last change: 2007-11-29

    for QVC Germany, Hueckelhoven
    by B+B Unternehmensberatung, Bad Duerkheim
    by E/S/P Dr. Beneicke, Heidelberg
'''
''' history:
    2006-08-24
        initial release
    2006-08-28
        fix: parse_lastcommands: openfile(...,'w') -> createfile()
        add: reportOn_last/lastb: no Top10 if no output
    2006-08-29
        fix: parse_lastcommands: 'last' output was skipped when user still online
        chg: parse_lastcommands: collect output lines in a list, write to file
             at once (to avoid empty output)
    2006-08-31
        add: lastb output now contains tty column
    2006-09-22
        chg: parse_lastcommands: use ttytype, not tty, for output to suppress specific tty info
    2006-09-25
        chg: use wdlib.open_out
    2006-09-26
        chg: sequence of command: failed first
        chg: no need for specific report routine for each cmd
        chg: parse_lastcommands: time filter on period
    2007-07-11
        fix: parse_lastcommands: outfmt provided only 7 instead of 10 places
             for duration
    2007-08-08
        chg: global variable __file__ sometimes undefined; wrapped
    2007-08-10
        fix: parse_lastcommands: check if command output is empty
    2007-11-29
        add: parse_lastcommands: sort output ascending
'''

import os, os.path, sys

# WDUX specific modules
import wdlib, lastlib as LL


# globals
try:
    test = __file__
except NameError:
    import sys
    __file__ = sys.argv[0]

__version__ = wdlib.mtime(__file__)
err = sys.stderr.write
LASTCOMMANDS = ('lastb', 'last')  # failed / successful logins



def parse_lastcommands(period):
    '''Run "last" and "lastb" commands, pipe the output to files.'''

    outfmt  = '%s  %-10s %-30s %-7s %-10s\n' # for last:  timestamp,user,host,tty,duration
    outfmt2 = '%s  %-10s %-30s %-7s\n'       # for lastb: timestamp,user,host,tty
    dtfmt = wdlib.DATE_LONG

    conf = wdlib.check_conf()
    # check all commands' output
    for cmd in LASTCOMMANDS:
        is_lastb = (cmd == 'lastb')

        # open pipe to command
        cmdline = conf.get('PLATFORM','%s_cmd' % cmd)
        child_in, child_out, child_err = os.popen3(cmdline)
        out = []  
        n = 0
        # get the data line-wise and write to list, filtering
        for line in child_out.readlines():
            this = LL.LastRecord(line,is_lastb)       # parse line
            if not this.OK:
                continue
            n += 1

            # filter on timestamp
            # as the output from the last commands is sorted by date, youngest
            # first, we can break at the first entry that is too old
            if this.dtserial >= period[1]: # older or equal to youngest
                continue
            if this.dtserial < period[0]:  # younger than oldest
                break

            if not is_lastb:
                if this.online:   # ... still online (no logout time)
                    duration = '     xx:xx'
                else:
                    duration = wdlib.elapsedstr(this.duration)
                out.append(outfmt % (wdlib.datestr(this.dtserial,dtfmt),
                    this.user, this.host, this.ttytype, duration))
            else: #  lastb output
                out.append(outfmt2 % (wdlib.datestr(this.dtserial,dtfmt),
                    this.user, this.host, this.ttytype))
        child_in.close()
        child_out.close()
        child_err.close()

        # error check:
        # n == 0: error in piped cmd!
        if not n:
            err('Error: no output from command "%s"!\n' % cmd)

        # write output to file
        if out:
            fname = cmd + '_out'
            f = wdlib.open_out(fname,'w')
            if not f:
                wdlib.info('parse_lastcommands(): cannot create %s!' % fname)
                continue
            wdlib.write_header(f,'system logins')
            # sort ascending before writing
            out.sort()
            f.writelines(out)
            f.close() 

    wdlib.info('')
    # -----------------
    return n
    # end of parse_lastcommands()



def reportOn_last(fh):
    '''Summarize events in output file and print to stdout.
    To summarize, skip date and time, count on keyfield.'''

    if 'lastb' in fh.name:
        desc = 'failed login attempts'
    else:
        desc = 'successful logins'

    category = [
                ( {}, desc + ' by user' ),
                ( {}, desc + ' by host' ),
                ( {}, desc + ' by tty/service' ),
               ]
    for line in fh:
        v = line.split()
        if not v:
            continue
        v[-1].rstrip()  # cut off EOL
        # count occurrences of keystr
        for i in range(len(category)):
            keystr = v[2 + i]  # we skip date and time columns
            category[i][0][keystr] = category[i][0].get(keystr,0) + 1

    for i in range(len(category)):
        dict_, desc = category[i]
        if dict_:
            wdlib.printTopN(dict_,desc)


def reportOn_lastcommands():
    ''' Report routine wrapper.
    Open files, call report routine for each source, close files.'''

    outpath = wdlib.out_path()
    for cmd in LASTCOMMANDS:
        fname = os.path.join(outpath,cmd + '_out')
        if os.path.isfile(fname):
            fh = wdlib.openfile(fname)
            if not fh:
                continue

            print wdlib.skip_header(fh),
            reportOn_last(fh)
            fh.close()
    

def main(filterOnTime=False):
    '''Run all subroutines necessary to process "last" commands.'''

    # prepare limit for time filter
    period = wdlib.set_timefilter('last_lastlog',filterOnTime)    
    
    # wake up operator
    print wdlib.version_header(__file__, '', period)
    
    # run the commands, write output files
    parse_lastcommands(period)

    # read output files and create report
    reportOn_lastcommands()
    
    # log status at end of processing
    wdlib.log_status('last_lastlog',is_OK=True)


# -----------------
# std: run script if not imported as a module
if __name__ == "__main__":
    wdlib.hint()
