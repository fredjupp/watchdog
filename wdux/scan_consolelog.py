#!/usr/bin/python
# -*- coding: iso-8859-1 -*-

''' WatchDog/UX module
    
    module name: scan_consolelog.py
    purpose    : scan console log file
    created    : 2006-07-04
    last change: 2007-11-24

    for QVC Germany, Hueckelhoven
    by B+B Unternehmensberatung, Bad Duerkheim
    by E/S/P Dr. Beneicke, Heidelberg    
'''
''' history:
    2006-08-24
        initial release
    2006-08-28
        chg: parse_consolelog: call countlines() with filename, not handle
    2006-09-18
        fix: parse: adjusted output format string for elapsedstr() which
             always has 10 chars
        chg: parse: will not record file offset after writing header (unused
             feature)
        fix: parse: wdlib.countlines() unreliable for unknown reasons;
             now output is counted on write
        fix: parse: all timestamps will be read now to obtain an accurate
             day roll-over; slows down processing a lot.
        chg: parse: day roll-over recognized when time is more than 1 min
             earlier than preceeding time
    2006-09-22
        chg: parse: store absolute normalized pathname in fname
        chg: parse: empty output files are deleted
        add: parse: output is sorted by timestamp now
        add: parse: console warnings now with timestamp
    2006-09-25
        chg: use wdlib.out_path
        chg: use timefmt for timestamps, w/o seconds
        chg: use dedicated logons dict for collecting logons, not _events
    2006-09-26
        chg: parse: time filter on period
        fix: parse: ignore incorrect backslash in job/session ID
    2006-10-24
        chg: parse: get file creation date before opening the logfile
        add: parse: print file creation date if interactive
    2006-10-25
        chg: integrated get_consolelog_path() from consoleloglib.py and deleted
             the library consloglib.py
        chg: parse: parse (artificial) timestamp lines in the logfile to get the
             correct date; use modified date if no such line encountered (yet)
             format: "HH:mm/YYYY-MM-DD/current timestamp"
    2007-07-31
        chg: main: abort if subroutines return error status
        fix: parse_: remember timestamp line time to detect rollover of next
             log entry
        add: parse_: display running line count approx. 10 times; (has to count
             lines twice)
    2007-08-08
        chg: global variable __file__ sometimes undefined; wrapped
    2007-08-10
        fix: main: if return False is used to signal a failure, an explicit
             return True must be coded when successful!
        fix: some err() statements without trailing newline
        fix: main: abort if logfile not accessible
    2007-09-10
        fix: typo 'lastm' instead of 'lasttm' prevents rollover detection
    2007-11-21
        chg: main: no check for log file existence (might be multi-file)
        chg: parse: determine starting date from current time if multiple
             logfiles are used
    2007-11-24
        chg: 1 of 2 file scans unnecessary if not in verbose mode
'''

import sys, os.path, time, re

# WDUX specific modules
import wdlib



# globals
try:
    test = __file__
except NameError:
    import sys
    __file__ = sys.argv[0]


__version__ = wdlib.mtime(__file__)

err = sys.stderr.write
timefmt='%Y-%m-%d %H:%M'  # output format of timestamp, w/o seconds


# list of counting dicts, descriptions and filenames
_events = {}  # defined in parse_consolelog()


def get_consolelog_path():
    '''Get path to console log file from config file.'''
    
    conf = wdlib.check_conf()
    if not conf:
        return None
    return conf.get('PATHS','console_log')


def timeserial(tmstr):
    '''Convert 'H:M' timestamp string to seconds.'''

    idx = tmstr.find(':')
    return (float(tmstr[:idx])* 60. + float(tmstr[idx+1:])) * 60.


def parse_consolelog(period,conspath=''):
    ''' Find logfile, parse content, write results to files.
    <period>: process only events within this period (serial times).
    '''
    
    # list of counting dicts, descriptions and filenames
    global _events

    # REs    
    isatime= re.compile(r'^\d?\d[:]\d\d$')   # contains a time [H]H:mm
    isadate= re.compile(r'''               # contains a date YYYY-[M]M-[D]D
        (?ix)                # ignore case, allow verbose RE
        ^
        (?P<year>\d{4,4})
        [-]
        (?P<month>\d{1,2})
        [-]
        (?P<day>\d{1,2})
        $
    ''')

    islogon = re.compile(r'''
        (?ix)                # ignore case, allow verbose RE
        ^\s*                 # skip w.sp. from BOL
        LOGON\s+for          # marker w/ embedded white space
        [^"]*["]             # until quote
        (?P<user>[^,]*)      # group 'user' not containg comma
        [,]                  # one comma
        (?P<queue>[^"]*)     # up to quote
        ["]
        \s+on\s+LDEV\s+      # marker w/ embedded white spacemarker
        (?P<ldev>\d+)        # group 'ldev': 1... numbers only
        \D*$                 # any non-numeric rest to EOL
    ''')
    
    islogoff = re.compile(r'''
        (?ix)                # ignore case, allow verbose RE
        ^\s*                 # skip w.sp. from BOL
        LOGOFF\s+on\s+       # marker w/ trailing w.sp.
        LDEV\s+[#]           # marker w/ embedded white space
        (?P<ldev>[\d]+)      # group 'ldev': 1... numbers only
        \D*$                 # any non-numeric rest to EOL
    ''')
    
    iswarning = re.compile(r'''
        (?ix)                # ignore case, allow verbose RE
        ^.*                  # skip junk from BOL
        WARNING:\s+          # marker w/ trailing w.sp.
        (?P<notice>.+[^\s])\s+
        USER\s+              # marker w/ trailing w.sp.
        (?P<user>[^\s]+)
        .*$
    ''')

    logons  = [{},{}]  # for collecting jobs/sessions:
                       #     {logtm,PID,user,queue,LDEV}
                       
    _events = [        # indices: [jobtype=session|job|warning][eventtype]
        [ # sessions
            {'name':'sessions_OK','desc':'sessions completed','out':[]},
            {'name':'sessions_nologon','desc':'sessions without logon','out':[]},
            {'name':'sessions_nologoff','desc':'sessions without logoff','out':[]}
        ],
        [ # jobs
            {'name':'jobs_OK','desc':'jobs completed','out':[]},
            {'name':'jobs_nologon','desc':'jobs without logon','out':[]},
            {'name':'jobs_nologoff','desc':'jobs without logoff','out':[]}
        ],
        [ # warnings
          # d is a list, not a dict!
            {'name':'console_warnings','desc':'console warnings','out':[]}
        ]
    ]
    # jobtypes
    jt_session = 0
    jt_job = 1
    jt_warn = 2
    jobtypes = (jt_session,jt_job,jt_warn)
    # eventtypes    
    ev_completed = 0
    ev_nologon = 1
    ev_nologoff = 2
    ev_warn = 0
    eventtypes = (ev_completed,ev_nologon,ev_nologoff)
    ev_legends = [
        '%-20s %10s %-10s %-15s %-4s %s' % ('login','duration','user',
                                            'queue','LDEV','PID'),
        '%-20s %-4s %s' % ('logoff','LDEV','PID'),
        '%-20s %-10s %-15s %-4s %s' % ('login','user','queue','LDEV','PID'),
        ]

    # as the console.log records times only, not dates,
    # we'll append the (creation) date of the file itself
    # approximation: use the modified time minus some margin
    # get the date before opening the file!
    if not wdlib.has_wildcards(conspath):
        sdate = os.path.getmtime(conspath) - (3*3600.)
    else:
        sdate = wdlib._curserial - (3*3600.)
    # truncate to midnight; logline's hh:mm will be added then
    startdate = wdlib.day_at_midnight(sdate)  # is a serial (sec since epoch)
    wdlib.info('\nparse_consolelog: assumed starting date of log entries: %s\n' \
        % wdlib.datestr(startdate,'%Y-%m-%d')) # debug

    log = wdlib.openfile(conspath)
    if not log:
        err('Cannot open %s. Aborted.\n' % conspath)
        return 0,0  # error abort

    # count line total for displaying percentage during scan
    if wdlib.verbose:
        linescounted = 0
        for line in log:
            linescounted += 1
        log.close()
        log = wdlib.openfile(conspath)
        step = linescounted // 10
        if not step: step = 2

    outpath = wdlib.out_path()
    for jt in jobtypes:
        for et in eventtypes:
            if et < len(_events[jt]):
                this = _events[jt][et]
                this['fname'] = fname = os.path.join(outpath,this['name'])
                this['fh'] = fh = wdlib.createfile(fname)
                if not fh:
                    err('parse_consolelog: cannot create %s. Aborted.\n' % fname)
                    return 0,0  # error abort

                # write header
                legend = ev_legends[et]
                if jt == jt_warn:
                    legend = '%-20s %-30s %s' % ('date','warning','user')
                wdlib.write_header(fh,this['desc'],legend)

    # -----------
    # start processing

    lasttm = 0.               # for detecting day rollover
    one_day = wdlib.one_day   # increment at day rollover
    nlines = ntotal = 0

    for line in log:          # read including EOL char
        ntotal += 1

        # display count up
        # can't use info() here because of \r usage
        if wdlib.verbose:
            if (ntotal % step) == 0:
                print >>sys.stderr,'%8s\r' % wdlib.pr(ntotal),

        if line.isspace():        # ...if only whitespace...
            continue

        part = line.split('/',3)  # need time, job ID, ID2, msg
        part = [x.strip() for x in part]

        # more checks on validity

        timestamp = part[0]
        # timestamp valid?
        if not isatime.match(timestamp):
            continue

        # recognize day rollovers before skipping lines

        # artificial timestamps might be inserted to get the 'real'
        # starting date, look for these:
        # format: "HH:mm/YYYY-MM-DD/current timestamp"
        if len(part) >= 3 and part[2] == "current timestamp":
            tm = isadate.match(part[1])
            if tm:
                # tm=(tm_year,tm_mon,tm_day,tm_hour,tm_min,tm_sec,tm_wday,tm_yday,tm_isdst)
                current = time.localtime() # need some values for fill-in...
                yr = int(tm.group('year'))
                mo = int(tm.group('month'))
                dy = int(tm.group('day'))
                startdate = time.mktime((
                        yr,mo,dy,
                        0, 0, 0,  # at midnight
                        current[6], current[7], current[8]  # wd, yd, isdst
                    ))
                wdlib.info('parse_consolelog: NEW assumed starting date of log \
entries: %s 00:00' % wdlib.datestr(startdate,'%Y-%m-%d'))

            # put this timestamp into lasttm to catch a possible rollover!!
            lasttm = startdate + timeserial(timestamp)

            # now discard this line
            continue
        
        # timestamp contains hour and minute only
        # and might repeat within a logfile
        # append a day,month,year from the starting date
        logtm = startdate + timeserial(timestamp)
        # increment day if this time is earlier than previous
        # last minute might be wrong, tolerate jitter
        if logtm < (lasttm - 120.):
            startdate += one_day
            logtm     += one_day
        lasttm = logtm   # keep for next loop

        # -----------
        # time filter
        if not period[0] <= logtm < period[1]:
            continue

        # skip line if this is not a valid entry for a job or a session
        if len(part) < 4:
            continue
        ID1 = part[1]
        
        if ID1[0] == '\\':
            ID1 = ID1[1:]
            
        jobtype = jt_session
        if not ID1.startswith('#S'):
            jobtype = jt_job
            if not ID1.startswith('#J'):
                jobtype = jt_warn
                if not ID1.startswith('#????'):
                    continue
        
        # line OK, read contents
        nlines += 1

        # ----------- next part
        # part[2]: second process ID
        PID = ID1 + '/' + part[2]

        # ----------- next part
        # evaluate REs only if necessary
        msg = part[3]
        a_logon = islogon.match(msg)
        if not a_logon:
            a_logoff = islogoff.match(msg)
            if not a_logoff:
                a_warning = iswarning.match(msg)
                if not a_warning:
                    # not of interest here, skip
                    nlines -= 1
                    continue
        if a_logon:
            # process LOGON
            user = a_logon.group('user')
            queue = a_logon.group('queue')
            ldev = a_logon.group('ldev')
            # just save infos and wait for logoff event
            logons[jobtype][PID] = (logtm, user, queue, ldev, PID)
        elif a_logoff:
            # process LOGOFF
            if PID in logons[jobtype]:
                logtm_in, user, queue, ldev, dummy = logons[jobtype][PID]
                del logons[jobtype][PID]
                # output
                out = _events[jobtype][ev_completed]['out']
                out.append('%-20s %-10s %-10s %-15s %-4s %s\n' % (
                    wdlib.datestr(logtm_in,timefmt),
                    wdlib.elapsedstr(logtm-logtm_in),
                    user, queue, ldev, PID))
            else:
                # logoff without logon
                ldev = a_logoff.group('ldev')
                # output
                out = _events[jobtype][ev_nologon]['out']
                out.append('%-20s %-4s %s\n' % (
                    wdlib.datestr(logtm,timefmt),
                    ldev, PID)
                    )
        elif a_warning:
            # record logtm, user, notice
            notice = a_warning.group('notice')
            user = a_warning.group('user')
            # output
            out = _events[jobtype][ev_warn]['out']            
            out.append('%-20s %-30s %s\n' % (
                wdlib.datestr(logtm,timefmt),
                notice, user)
                )
            
    log.close()
    
    # remaining logons are non-logoff events
    for jobtype in (jt_session,jt_job):
        inlist = logons[jobtype].values()
        out = _events[jobtype][ev_nologoff]['out']
        for x in inlist:
            (logtm, user, queue, ldev, PID) = x
            out.append('%-20s %-10s %-15s %-4s %s\n' % (
                wdlib.datestr(logtm,timefmt), user, queue, ldev, PID))

    # actually write the files; delete if empty
    for e in _events:
        for j in e:
            fh = j['fh']
            _list = j['out']
            if not len(_list):
                fh.close()
                wdlib.rm(j['fname'])
            else:
                _list.sort()
                for line in _list:
                    fh.write(line)
                fh.close()


    # output: counts and file references
    for e in _events:
        for j in e:
            n = len(j['out'])
            if n:
                print '%-30s: %7d (see file %s)' % (j['desc'], n, j['name'])
            else:  # file empty
                print '%-30s: %7d (%s)' % (j['desc'], 0, 'no output')

    # ----------------
    # done processing CONSOLE.LOG
    return (ntotal, ntotal-nlines)

    # ----------- end of parse_consolelog()



def main(filterOnTime=True):    
    '''Run all subroutines necessary to process the console log.
    params:
    <filterOnTime>: if False, the timestamp of the last run in the
    config file is ignored, i.e. all entries will be processed
    regardless of age.
    '''

    # prepare limits for time filter
    period = wdlib.set_timefilter('last_consolelog',filterOnTime)    

    # locate logfile
    conspath = get_consolelog_path()
    if not conspath:
        err('No console logfile specified. Aborted.\n')
        return False

    # wake up operator
    print wdlib.version_header(__file__,conspath,period)

    # main processing step:
    # parse console log and print results
    ntotal, nskipped = parse_consolelog(period,conspath)
    if not ntotal:
        return False

    # log status at end of processing
    wdlib.log_status('last_consolelog',is_OK=True)

    wdlib.info('console log: lines read/skipped/parsed: %s %s %s' % (
        wdlib.pr(ntotal), wdlib.pr(nskipped), wdlib.pr(ntotal-nskipped)))

    return True  # main()

# -----------------
# std: run script if not imported as a module
if __name__ == "__main__":
    wdlib.hint()
