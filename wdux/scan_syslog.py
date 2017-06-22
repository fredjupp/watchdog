#!/usr/bin/python
# -*- coding: iso-8859-1 -*-
''' WatchDog/UX module
    
    module name: scan_syslog.py
    purpose    : scan syslog file
    created    : 2006-08-04
    last change: 2007-11-24

    for QVC Germany, Hueckelhoven
    by B+B Unternehmensberatung, Bad Duerkheim
    by E/S/P Dr. Beneicke, Heidelberg
'''
''' history:
    2006-08-24
        initial release
    2006-08-30
        fix: main: skipIfNotParsed was always True; now read from conf file
        fix: reportOn_allsources: '_OK' files were opened even though keep_OK
             was False
    2006-09-01
        fix: reportOn_allsources: check for OK files did not catch empty
             FAIL files; now check file existence instead
    2006-09-18
        fix: parse_sudo: COMMAND may contain semicolon(s) and white space
        fix: reportOn_general: optionally skip more columns when reporting
    2006-09-25
        fix: parse_ftpd: _FAIL output needs to have 3 columns just like _OK
             otherwise report will contain garbled message
        fix: reportOn_general: no continuation dots if msg is shorter
        chg: reportOn_general: words to keep is a parameter (e.g. 1 for sudo)
             enhancing the information content of the report
        chg: open_inouterr, reportOn_allsources: use wdlib.out_path
        chg: FAIL keywords added: 'deactivat', 'forbidden'
    2006-09-26
        chg: split_syslog: time filter on period
    2007-07-31
        chg: main: abort if no path to syslog file
        chg: main: abort if split_syslog and parse_allsources return error status
        add: open_inouterr: propagate error status
        add: split_syslog: return error status to caller
        chg: removed time module import
        chg: integrated get_syslog_path() from sysloglib.py
        chg: get_syslog_path: always read path, no default, no param
    2007-08-08
        chg: global variable __file__ sometimes undefined; wrapped
    2007-08-10
        fix: various: if return False is used to signal a failure, an explicit
             return True must be coded when successful!
        fix: some err() statements without trailing newline
        fix: main: abort if logfile not accessible
    2007-11-21
        add: split_syslog: added virgin flag for each output file to see if it
             has been written to (replaces filehandle.tell())
        fix: split_syslog: specify write mode for open_tmp call
    2007-11-24
        chg: main: no check for log file existence (might be multi-file)
        add: parse_*: added virgin flag for each tmp file to see if it
             has been written to (replaces filehandle.tell())
        add: added 'dead' keyword for unknown sources
'''

import sys              # for sys.maxint
import os, re

# WDUX specific modules
import wdlib
import sysloglib as SLL


# globals
try:
    test = __file__
except NameError:
    import sys
    __file__ = sys.argv[0]

__version__ = wdlib.mtime(__file__)

err = sys.stderr.write
TopN = 10
OTHERSOURCE = '_system_' # substitute for sources not processed here

sources = {
    # 'source_name' {base_filename, description, keep successful events?}
    # syslog is split by 'source_name' (lowercase!) into files in TMP
    # these are then read by the parser, results go into OUT
    # 'source_name' must match the syslog entry exactly! except for case
    # unrecognized sources are put into the OTHERSOURCE category
    # 'tmp_fh','handles','fname' values added at runtime
    'ftpd':      {'name':'sys_ftp','desc':'FTP events','keep_OK':True},
    'jdbcsrvr':  {'name':'sys_jdbc','desc':'JDBC server events','keep_OK':False},
    'rlogind':   {'name':'sys_rlogin','desc':'rlogin events','keep_OK':False},
    'sshd':      {'name':'sys_ssh','desc':'ssh events','keep_OK':False},
    'su':        {'name':'sys_su','desc':'su events','keep_OK':True},
    'sudo':      {'name':'sys_sudo','desc':'sudo events','keep_OK':True},
    'telnetd':   {'name':'sys_telnet','desc':'telnet events','keep_OK':False},
    OTHERSOURCE: {'name':'sys_unknown',
                  'desc':'events from unrecognized sources','keep_OK':False},
}
all_sources = sources.keys()


def get_syslog_path():
    '''Get path to syslog file from config file.'''

    conf = wdlib.check_conf()
    if not conf:
        return None
    return conf.get('PATHS','syslog')


def split_syslog(period, slpath, skipIfNotParsed=True, sourcesToDo=all_sources):
    '''Find logfile, separate content by source, write to tmpfiles.
    <period>: process only events younger within this period (serial times)
    <sourcesToDo>: list of source names to process
    <skipIfNotParsed>: process entries only for sources for which
    parsers exist (ftp, ssh, rlogin, telnet, jdbc, su, sudo)
    '''

    global sources

    logfile = wdlib.openfile(slpath)
    if not logfile:
        return 0,0

    # if we do not process sources for which there is no parser,
    # then delete the OTHERSOURCE key in sources:
    if skipIfNotParsed:
        del sources[OTHERSOURCE]
    # exclude sources if parameter <sourcesToDo> is specified
    if sourcesToDo != all_sources:
        for s in sources.keys():
            if s not in sourcesToDo:
                del sources[s]

    # create target files in advance
    for source in sources:
        d = sources[source]
        fh = wdlib.open_tmp(d['name'],'w')
        if not fh:
            return 0,0

        # store values for later usage
        d['tmp_fh'] = fh
        d['fname']  = fh.name  # the expanded form
        d['virgin'] = True


    # -----------------------
    # start splitting up syslog file
    '''Parsing is done when creating a SyslogRecord.
    SyslogRecord delivers:
    .OK              : no parsing error (e.g. 'repeats' messages)
    .src             : data source, lowercase
    .dtserial        : timestamp in seconds since epoch
    .hostname        : originating host
    .PID             : process ID, if present
    .msg             : the log message, unparsed
    '''
    
    nlines = ntotal = 0
    for line in logfile:                       # read including EOL char
        ntotal += 1
        if not line:                           # skip empty lines
            continue
        
        # pre-check
        if skipIfNotParsed:
            found = False
            ll = line.lower()
            for token in sources:
                if token in ll:
                    found = True
                    break
            if not found:
                continue  # ...with next line
        
        this = SLL.SyslogRecord(line)       # parse line
        if not this.OK:                     # skip errors
            continue
        if this.src not in sources:
            if skipIfNotParsed:
                continue
            this.src = OTHERSOURCE

        nlines += 1
        # time filter and output
        if period[0] <= this.dtserial < period[1]:   # then append to output file
            sources[this.src]['tmp_fh'].write('%.0f %s %s\n' % (
                this.dtserial,this.PID,this.msg) )
            sources[this.src]['virgin'] = False  # this output file is non-empty
    logfile.close()
    # ----------------
    # done writing split files in TMP
    # delete unused output files
    for i in sources.keys():
        fh = sources[i]['tmp_fh']
        fh.close()
        if sources[i]['virgin']:
            wdlib.rm(fh.name)
            del sources[i]
    
    # ----------------
    # done split_syslog()
    return ntotal, (ntotal-nlines)


''' parser routines
filtered by
1) messages to ignore and
2) messages with errors
if more specific post processing needs to be done, a special
parser routine is used (e.g. for ftpd, su, sulog)'''

# two regular expressions: one general 'catch errors' and
# the exception to the rule

_cRE_iserrormsg = re.compile(r'''
    (?ix)                     # ignore case, allow verbose RE
    (?:                       # group of alternatives
         break(-)?in
        |critical
        |denied
        |deactivat
        |disabled
        |error
        |fail(ed)?
        |forbidden
        |illegal
        |incorrect
        |(not\s+allowed)
        |refused
        |violat
        |dead
    )
''') 

_cRE_ignoremsg = re.compile(r'''
    (?ix)                     # ignore case, allow verbose RE
    (?:                       # ignorable:
         peer\s+died              # (telnet)
        |failover                 # (system)
        |by\s+peer
    )
''')


def parse_general(d):
    ''' General filter on error messages.'''

    global _cRE_ignoremsg, _cRE_iserrormsg
    
    fin, fout, ferr = d['handles']
    keep_OK = d['keep_OK']
    for line in fin:  # with EOL char
        v = line.split(None,2) # date serial,PID,[msg]
        if len(v) == 3:        # with message field
            msg = v[2]
            if _cRE_ignoremsg.search(msg):
                continue
            if _cRE_iserrormsg.search(msg):
                ferr.write(wdlib.datestr(float(v[0])) + ' ' + msg)
                d['virgin'][2] = False
            elif keep_OK:
                fout.write(wdlib.datestr(float(v[0])) + ' ' + msg)
                d['virgin'][1] = False

    
def parse_ftpd(d):
    ''' Parse ftpd entries.'''

    # RE for the message part if src == 'ftpd'
    _cRE_FTPmsg = re.compile(r'''
        (?ix)                        # ignore case, allow verbose RE
        ^                            # from BOL
        (?:
            \s*                          # opt. white space
            FTP                          # keyword
            \s*?
            (?P<login>LOGIN\s*?FROM)     # 'LOGIN FROM' key phrase
            \s+                          # white space, greedy
            (?P<fromhost>[^,]+)          # hostname [hostIP]
            [,]                          # mandatory
            \s*                          # opt. white space, greedy
            (?P<user>.+)                 # FTP username
        ) | (?:
            (?P<close>FTP\s*?session\s*?closed) # key phrase
        )
        \s*$                         # EOL
    ''') 

    fin, fout, ferr = d['handles']
    keep_OK = d['keep_OK']
    logins = {}
    for line in fin:  # with EOL char
        v = line.split(None,2) # date serial/PID/[msg]
        if len(v) == 3:        # with message field
            tstamp = float(v[0])
            msg = v[2]
            if _cRE_iserrormsg.search(msg):
                # we introduce a third column '!' to make the failed output
                # compatible with _OK output where the 3rd column is
                # skipped when reporting
                ferr.write(wdlib.datestr(tstamp) + ' ! ' + msg)
                d['virgin'][2] = False
            elif keep_OK:              # normal FTP msg
                PID = v[1]
                mo = _cRE_FTPmsg.match(msg)
                if mo:         # login or close
                    # yield: login,fromhost,user
                    if mo.group('login'):
                        # collect login by PID
                        logins[PID] = (tstamp,mo.group('fromhost'),mo.group('user'))
                    else:
                        # until FTP session closed
                        if PID in logins:
                            tlogin, fromhost, user = logins[PID]
                            duration = wdlib.elapsedstr(tstamp - tlogin)
                            dt = wdlib.datestr(tlogin)
                            fout.write('%(dt)s %(duration)s %(user)s@%(fromhost)s\n' % vars())
                            d['virgin'][1] = False
                            del logins[PID]
                        # FTP close without login: login refused et al., see FTP_FAILED
    del logins


def parse_su(d):
    '''Parse su entries.'''

    # RE for the message part if src == 'su'
    _cRE_SUmsg = re.compile(r'''
        (?ix)                        # ignore case, allow verbose
        ^                            # from BOL
        (?:
            \s*?                         # white space, non greedy, opt.
            (?P<status>[+-])             # keyword
            \s+                          # white space, greedy
            (?P<tty>[^\s]+)              # tty line
            \s+                          # white space, greedy
            (?P<fromuser>[^-]+)          # who
            [-]                          # mandatory
            (?P<asuser>[^\n]+)           # as whom
        )
        \s*$                         # EOL
    ''') 

    fin, fout, ferr = d['handles']
    keep_OK = d['keep_OK']
    for line in fin:  # with EOL char
        v = line.split(None,4)       # date serial/PID/status/tty/who-aswhom
        dt = wdlib.datestr(float(v[0]))
        # PID = v[1] is None, ignored here
        # tty
        tty = v[3]
        # might be: 'console', 'unknown', 'tty??', 'ftp', 't3'
        if tty[0] == 't' or tty.isdigit():
            tty = 'pts'
        # users
        who,whom = v[4].rstrip().split('-',1)
        out = '%(dt)s %(who)-12s as %(whom)-12s on %(tty)11s\n' % vars()
        if v[2] == '-':    # FAIL or OK
            ferr.write(out)
            d['virgin'][2] = False
        elif keep_OK:
            fout.write(out)
            d['virgin'][1] = False


def parse_sudo(d):
    ''' Parse sudo entries.'''

    # RE for the message part if src == 'sudo'
    _cRE_msg = re.compile(r'''  # msg
        (?ix)                   # ignore case, allow verbose RE
        ^
        \s*
        (?:
            (?:  # optional first term
                (?P<cause>[^=\s][^=]+[^=\s])\s*[;]\s*
            )?  
            (?:
                TTY=(?P<tty>[^;\s]+)\s*[;]?
                \s*
                PWD=(?P<pwd>[^;\s]+)\s*[;]?
                \s*
                USER=(?P<whom>[^;\s]+)\s*[;]?
                \s*
                COMMAND=(?P<cmd>.+)    # cmd may contain semicolon and wh.sp.
                \s*
                $
            )
        )
        \s*$
    ''')

    fin, fout, ferr = d['handles']
    keep_OK = d['keep_OK']
    for line in fin:  # with EOL char
        v = line.split(None,4) # date serial/PID/who/':'/(msg;)?(TTY=;PWD=;USER=;COMMAND=;)
        dt = wdlib.datestr(float(v[0]))
        # PID = v[1] is None, ignored here
        who = v[2]
        # v[3] is ':'
        # v[4] is the message part
        mo = _cRE_msg.search(v[4])
        if not mo:
            print 'parse_sudo(): error parsing ' + v[4]
            continue
        cause = mo.group('cause')
        tty = mo.group('tty')
        pwd = mo.group('pwd')
        whom = mo.group('whom')
        cmd = mo.group('cmd')
        msg = '%(cmd)s in %(pwd)s' % vars()
        if cause:
            msg = '%(cause)s: ' % vars() + msg
        out = '%(dt)s %(who)-12s as %(whom)-12s on %(tty)7s: %(msg)s\n' % vars()
        if _cRE_iserrormsg.search(v[4]):
            ferr.write(out)
            d['virgin'][2] = False
        elif keep_OK:
            fout.write(out)
            d['virgin'][1] = False


# as long as the general filtering on 'failed' entries can be used,
# call the parse_general() routine:
parse_jdbcsrvr = parse_general
parse_rlogind  = parse_general
parse_sshd     = parse_general
parse_telnetd  = parse_general
parse__system_ = parse_general


def parse_allsources():
    ''' Parser routine wrapper.

    Open files, call specific parser for each source,
    delete unused output files. If there is no output from a source,
    the source dict entry is deleted.'''

    global sources

    def open_inouterr(infile):
        ''' Open tmp file <infile> for reading, create 2 output files
        with same name + '_OK' and '_FAIL' in output dir.
        Return 3 file handles.
        '''
        
        fin = wdlib.openfile(infile)
        if not fin:
            return None,None,None
            
        outfile = os.path.basename(infile) + '_OK'
        fout = wdlib.open_out(outfile,'w')
        if not fout:
            return None,None,None

        outfile = os.path.basename(infile) + '_FAIL'
        ferr = wdlib.open_out(outfile,'w')
        if not ferr:
            return None,None,None

        return fin, fout, ferr


    for source in sources.keys():
        d = sources[source]
        # open files; fin in TMP dir, fout/ferr in output dir
        d['handles'] = (fin, fout, ferr) = open_inouterr(d['fname'])
        if not fin:
            return False
        wdlib.write_header(fout,'successful ' + d['desc'])
        wdlib.write_header(ferr,'failed ' + d['desc'])
        # flag if output data present
        d['virgin'] = {}
        d['virgin'][0] = d['virgin'][1] = d['virgin'][2] = True
        # virgin flag of fin will stay True, file will always be deleted

        # call source specific parser
        eval('parse_%s(d)' % source, globals(), locals())

        # close all, delete input file and empty output file(s)
        left = 3
        for i in (0,1,2):
            fh = d['handles'][i]
            fh.close()
            if d['virgin'][i]:
                wdlib.rm(fh.name)
                left -= 1

        if not left:     # no output for this source
            del sources[source]

    return True  # parse_allsources()


def reportOn_general(d, skip=2, wordstokeep=3):
    '''Summarize events in output files and print to stdout.
    To summarize, skip date and time (skip == 2), or more
    (ftp_OK skips 3rd column: duration)
    shorten message to <wordstokeep> and count.'''

    fh = d['handles']
    print wdlib.skip_header(fh),
    if '_FAIL' in d['fname']:
        desc = 'failed ' + d['desc']
    else:
        desc = 'successful ' + d['desc']

    reason = {}
    for line in fh:
        v = line.split(None,skip)  # date, time, msg
        msgstr = v[-1][:-1]
        # skip 'xxx:' part if present
        i = msgstr.find(':')
        msg = msgstr[i+1:].split()
        msg = [m.strip() for m in msg]
        # keep (up to) <wordstokeep> words only
        if len(msg) > wordstokeep:
            keystr = ' '.join(msg[:wordstokeep]) + '...'
        else:
            keystr = ' '.join(msg)

        reason[keystr] = reason.get(keystr,0) + 1   # count

    wdlib.printTopN(reason,desc)


    
# call the reportOn_general() routine if nothing special is necessary:
def reportOn_ftpd(d):
    reportOn_general(d,3)
    
def reportOn_sudo(d):
    reportOn_general(d,3,1)
    
reportOn_jdbcsrvr = reportOn_general
reportOn_rlogind  = reportOn_general
reportOn_sshd     = reportOn_general
reportOn_su       = reportOn_general
reportOn_telnetd  = reportOn_general
reportOn__system_ = reportOn_general


def reportOn_allsources():
    ''' Report routine wrapper.

    Open files, call specific report routine for each source, close files.'''

    global sources

    outpath = wdlib.out_path()
    # see which output files exist
    for source in sources:
        d = sources[source]
        for part in ('_FAIL','_OK'):
            d['fname'] = fname = os.path.join(outpath,d['name'] + part)
            if os.path.isfile(fname):  # catches empty files AND non-existing ones
                # run reportOn_<source>
                d['handles'] = fh = wdlib.openfile(fname)
                if not fh:
                    wdlib.info('report: cannot open %s\n' % fname)
                    continue
                # call source specific routine
                reporter = 'reportOn_%s(d)' % source
                eval(reporter, globals(), locals())
                fh.close()
    

def main(filterOnTime=True,sourcesToDo=all_sources):    
    '''Run all subroutines necessary to process the syslog.
    params:
    <filterOnTime>: if False, the timestamp of the last run in the
    config file is ignored, i.e. all entries will be processed
    regardless of age.
    <sourcesToDo>: list of sources to process; defaults to all
    '''
    
    # prepare limit for time filter
    period = wdlib.set_timefilter('last_syslog',filterOnTime)    
    
    # locate logfile
    slpath = get_syslog_path()
    if not slpath:
        err('scan_syslog: Cannot find syslog file "%s". Aborted.\n' % slpath)
        return False

    # wake up operator
    print wdlib.version_header(__file__,slpath,period)

    # split syslog into tmp files, one for each source
    skipIfNotParsed = wdlib.boolfromconf('CHECKVALUES','SYSLOG_SKIP_UNKNOWN')

    ntotal, nskipped = split_syslog(period,slpath,skipIfNotParsed,sourcesToDo)
    wdlib.info('syslog: lines read/skipped/parsed: %s %s %s' % (
        wdlib.pr(ntotal), wdlib.pr(nskipped), wdlib.pr(ntotal-nskipped)) )

    if not ntotal:
        return False
    
    # parse the data files, write output files, delete input tmp files
    if not parse_allsources():  # exec parser
        return False
    
    # read output files and create report
    reportOn_allsources()
    
    # log status at end of processing
    wdlib.log_status('last_syslog',is_OK=True)

    return True  # main()

# -----------------
# std: run script if not imported as a module
if __name__ == "__main__":
    wdlib.hint()
