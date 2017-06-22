#!/usr/bin/python
# -*- coding: iso-8859-1 -*-

''' -----------------------------------------------------
    WatchDog UX module
    
    module name: wdux.py
    purpose:     main script, calls various scanners,
                 writes output files and prints reports
    created    : 2006-06-29
    last change: 2008-01-23
    
    for QVC Germany, Hueckelhoven
    by B+B Unternehmensberatung, Bad Duerkheim
    by E/S/P Dr. Beneicke, Heidelberg
    -----------------------------------------------------
'''
''' history:
    2006-08-24
        initial release
    2006-08-25
        fix: main: wrong index on '-l' option boolean
        fix: main: get_reportname() called before existence of conf file was
             confirmed
        fix: make_copies: strip daily date from report filename when copying
             to daily dir
        fix: main: now output files are not copied if output file is specified
             on cmdline
        fix: indendation around convEOL() call corrected
    2006-08-29
        chg: WINPATH conf entry no longer needed/written
        chg: mail renamed to sendmail
        add: main: wdux_header() called twice to be included in report
        add: main: final msg at end of report
    2006-08-30
        fix: get_reportname: today's date was fetched from conf file before it
             was written to it; replaced by function
        chg: main: list of modules used instead of enumeration
        add: output and tmp dirs are removed before run; otherwise, a report
             may be generated with stale (old) data
        chg: make_copies: worked over; file extension handling
        chg: daily dir format leading '_' removed, dirs renamed
    2006-09-25
        chg: create_folderstructure: do not delete tmp folder
             anymore (might be system tmp folder)
        chg: create_folderstructure: use clearfolder instead of rmdir on
             output folders
        fix: convert_conf: did not convert '_*' daily dirs
    2006-09-26
        chg: extended wdux_header (title, date, hostname)
        add: contents struct; print_overview
        chg: reshuffled options in conf.file to group options that are written
             together in sections CURRENT RUN and STATUS
    2006-09-27
        add: has_all_conf_options(): check all mandatory config parameters
             beforehand
        chg: conf param 'PATHS/OUT_PATH' removed
    2007-07-30
        chg: main: abort if stdout cannot be redirected to report file
        chg: crucial() integrated into has_all_conf_options()
        chg: cleanup: exit(failed) instead of exit(1)
    2007-08-08
        chg: global variable __file__ sometimes undefined; wrapped
        chg: global separator line (sep) for all occurrences
        chg: wdux_header: wdlib.center made local
        chg: main: verbose flag is set at runtime, not in module wdlib
    2007-08-09
        add: create_folder_structure: added error exits
    2007-08-10
        chg: print_overview: renamed global var 'contents' to 'module_descriptions'
        add: make_copies: quit silently if nothing to copy
        fix: various: if return False is used to signal a failure, an explicit
             return True must be coded when successful!
        fix: some err() statements without trailing newline
    2007-08-11
        chg: make_copies: reports in daily folder must have unique names
             as there might be several different ones there
        chg: daily folders moved to subfolder 'DAILY'
        fix: convert_conf: folders not renamed if DAILY_FMT setting was correct
             which is independent of each other
    2007-08-24
        add: get_clusterstatus(), global vars cl_pkg, cl_sts
        add: cluster status in report header
    2007-11-29
        fix: convert_conf: test for and prefix 'DAILY' string using OS specific
             routines
    2007-12-05
        chg: dailydir: use wdlib.datestr() like everywhere else
        chg: get_reportname: do not force date in reportname but allow
             date placeholders
    2007-12-11
        fix: convert_conf: wrong action if path already contained 'daily'
        chg: daily_dir, create_folder_structure: path is not set to uppercase
             any more
    2008-01-23
        fix: has_all_conf_options(): wrong (undef) variable used in error msg
             after rename of 'x' to 'parameter_tuple'
'''



import os, os.path, sys
import time, datetime
import optparse
import shutil

# WDUX specific modules
import wdlib
import check_passwd
import scan_syslog
import scan_consolelog
import scan_last



# globals
try:
    test = __file__
except NameError:
    import sys
    __file__ = sys.argv[0]

__version__ = wdlib.mtime(__file__)

reportname = ''  # filename of redirected stdout
err = sys.stderr.write
sep = '_' *wdlib.nDashes  # separator line
# cluster status:
cl_sts = False  # True=up, False=down
cl_pkg = ''

module_descriptions = { # modulename, desc
    'scan_syslog':    ['failed FTP events',
                       'successful FTP events',
                       'failed JDBC server events',
                       'failed rlogin events',
                       'failed ssh events',
                       'failed su events',
                       'successful su events',
                       'failed sudo events',
                       'successful sudo events',
                       'failed telnet events',
                       'failed events from unrecognized sources',
                       ],
    'scan_consolelog': ['sessions completed',
                        'sessions without logon',
                        'sessions without logoff',
                        'jobs completed',
                        'jobs without logon',
                        'jobs without logoff',
                        'console warnings'
                       ],
    'scan_last':       ['Top 10 failed login attempts by user',
                        'Top 10 failed login attempts by host',
                        'Top 10 failed login attempts by tty/service',
                        'Top 10 successful logins by user',
                        'Top 10 successful logins by host',
                        'Top 10 successful logins by tty/service'
                       ],
    'check_passwd':    ['ERROR: Users having a duplicate UID',
                        'WARNING: Users with more than one login name',
                        'WARNING: Users with multiple accounts (according to comment)',
                        'WARNING: Users with shared passwords',
                        'ERROR: Users with empty passwords',
                        'INFO: Super-users (UID == 0)',
                        'INFO: Users with unusual shells',
                       ],
}



def print_overview(mods, verbose=False):
    ''' Print list of selected modules and their description (default).'''

    ct = 0
    print '\nOverview of selected modules and tests\n'
    for m in mods:
        ct += 1
        modname = m.__module__
        print '%d. %s' % (ct,modname)
        if verbose:
            for desc in module_descriptions[modname]:
                print '\t',desc
    print '\nNot all tests of the selected modules may result in output.'
    print sep


def wdux_header(confpath):
    import platform
    center = wdlib.center

    print sep
    print
    center('              ##                ')
    center('              ##                ')
    center('##     ##  #####  ##  ##  ##  ##')
    center(' ## # ##  ##  ##  ##  ##    ##  ')
    center('  ## ##    #####   ####   ##  ##')
    print
    print
    center('WatchDog/UX Daily Report')
    center('%s' % time.strftime('%A %d.%m.%Y %H:%M'))
    center(r'on host "%s"' % (platform.uname()[1]))
    print
    print
    center('wdux version %s' % __version__)
    center('configuration from "%s"  [%s]' % (confpath,wdlib.mtime(confpath)))
#    center('cluster package: %s       status: %s' % (cl_pkg, cl_sts))
    print sep


def wdux_endheader():
    print sep
    print 'End of Daily Report.'
    print sep


def dailydir(root=''):
    ''' Return the name of the weekday folder.'''

    conf = wdlib.check_conf()
    dailyfmt = conf.get('OUTPUT','DAILY_DIR_FMT')   # '1-MON'
    s = wdlib.datestr(wdlib._curserial,dailyfmt)
    return os.path.join(root,s)


def get_reportname():
    conf = wdlib.check_conf()

    root = conf.get('CURRENT RUN', 'OUTPATH')
    nametemplate = conf.get('OUTPUT','REPORT_NAME')
    # might contain placeholders for date e.g. %Y,%M,%D,%w,%a
    repname = wdlib.datestr(wdlib._curserial,nametemplate)
    p = os.path.join(root,repname)
    return wdlib.abspath(p)


def make_copies(absreportname):
    '''copy report to weekday folder
    then, copy all files to WIN_ROOT folder, converting them to DOS style
    line ends.'''
    
    # sanity check
    if not os.path.isfile(absreportname):
        return
    
    conf = wdlib.check_conf()

    arch_root = wdlib.abspath(conf.get('OUTPUT','arch_root'))
    win_root = wdlib.abspath(conf.get('OUTPUT','win_root'))
    win_ext = conf.get('OUTPUT','win_ext')
    repname = os.path.basename(absreportname)

    # copy report to daily dir
    destname = os.path.join(dailydir(arch_root),repname)
    shutil.copy2(absreportname,destname)
    # copy DOS converted file to daily dir
    wdlib.convEOL(destname,True,dailydir(win_root),win_ext)

    # copy and convert all files from ARCH_ROOT to WIN_ROOT
    root = conf.get('CURRENT RUN', 'OUTPATH')
    dest = root.replace(arch_root,win_root)
    for f in os.listdir(root):
        af = os.path.join(root,f)
        if os.path.isfile(af):
            wdlib.convEOL(af,toDOS=True,destdir=dest,DOSext=win_ext)


def sendmail(filename):
    ''' Send <filename> per eMail.'''
    conf = wdlib.check_conf()

    host =  conf.get('CURRENT RUN','host')
    subject = conf.get('MAIL','subject') + ' on ' + host
    receiver = conf.get('MAIL','touser')
    cmd = 'mailx -s "%(subject)s" %(receiver)s < %(filename)s' % vars()
    wdlib.try_system(cmd)


def convert_conf():
    '''Convert wdux.conf file once to make changes easier.'''
    conf = wdlib.check_conf()

    # move/remove option <opt> from <oldsect> to <newsect>
    # remove if <newsect> is empty
    moves = [  # oldsect, option, newsect
        ('CURRENT RUN','REPPATH',''),
        ('CURRENT RUN','WINPATH',''),
        ('CHECKVALUES','PASSWD_NUMFIELDS',''),
        ('PATHS','PROG_DIR',''),
        ('PATHS','OUT_DIR',''),
        # next 3: moved to section CURRENT RUN; remove only, are added on init
        ('PLATFORM','OS',''),
        ('PLATFORM','HOST',''),
        ('OUTPUT','TODAY',''),
       ]
    for (oldsect, opt, newsect) in moves:
        if conf.has_section(oldsect):
            if conf.has_option(oldsect,opt):
                if newsect:
                    x = conf.get(oldsect,opt)
                    conf.add(newsect,opt,x)
                conf.remove_option(oldsect,opt)
            # section empty?
            opts = conf.options(oldsect)
            if not len(opts):
                conf.remove_section(oldsect)

    # new options
    if not conf.has_option('CHECKVALUES','SYSLOG_SKIP_UNKNOWN'):
        conf.add('CHECKVALUES','SYSLOG_SKIP_UNKNOWN',False)

    # 2007-08-11: put daily folders in subfolder DAILY
    dailyfmt = os.path.normpath(conf.get('OUTPUT','DAILY_DIR_FMT'))
    # '1-MON' or 'path/1-MON'
    if not dailyfmt.count(os.path.sep):  # contains no path
        dailyfmt = os.path.join('DAILY',dailyfmt)  # prepend folder path
    conf.add('OUTPUT','DAILY_DIR_FMT', dailyfmt)
    conf.save()

    # there might exist output dirs, rename to preserve archived files
    # this is a one-time only procedure
    # and depends on a specific format for the daily dirs
    dailyfmt = conf.get('OUTPUT','DAILY_DIR_FMT')   # '1-MON' or 'path/1-MON'
    subfolder = os.path.dirname(dailyfmt)
    arch_root = conf.get('OUTPUT','arch_root')
    win_root = conf.get('OUTPUT','win_root')
    for root in (arch_root, win_root):
        if os.path.isdir(root):
            for d in os.listdir(root):
                ad = os.path.join(root,d)
                if os.path.isdir(ad) and len(d) == 5:
                    if d[0] in '0123456' and d[1] == '-':
                        nd = os.path.join(root,subfolder,d)
                        try:
                            os.rename(ad,nd)
                        except OSError:
                            pass


def has_all_conf_options(confpath):
    '''Check all mandatory sections and options in specified conf file.'''
    
    needed = [ # sect, opt, value example or range, desc
        ('CHECKVALUES','SYSLOG_SKIP_UNKNOWN','True|False',
             'while scanning syslog.log, whether data from sources for which no parser exists are ignored'),
        ('CLUSTER','cluster_package','p1',
             'name of the cluster package'),
        ('CLUSTER','cluster_cmd','/usr/sbin/cmviewcl -p',
             'command to query the cluster status for package <arg1>'),
        ('MAIL','subject','WatchDog/UX report',
             'subject line for the mailed report'),
        ('MAIL','touser','admins',
             'recipients of mailed report'),
        ('OUTPUT','ARCH_FMT','%Y-%m-%d',
             'C-style format string for naming daily output folders'),
        ('OUTPUT','ARCH_ROOT','ARCHIVE',
             'root of UNIX text format output files'),
        ('OUTPUT','DAILY_DIR_FMT','%w-%a',
             'C-style format string for naming weekday output folders'),
        ('OUTPUT','REPORT_NAME','report',
             'name of report file'),
        ('OUTPUT','WIN_EXT','txt',
             'filename extension for Windows text files, w/o leading dot'),
        ('OUTPUT','WIN_ROOT','WIN',
             'root of Windows text format output files'),
        ('PATHS','CONSOLE_LOG','<name>',
             'full path to console.log file'),
        ('PATHS','FILES_DIR','files',
             'path for root containing TMP_DIR'),
        ('PATHS','PASSWD','/etc/passwd',
             'path to password file'),
        ('PATHS','SYSLOG','/var/adm/syslog.log',
             'path to syslog file'),
        ('PATHS','TMP_DIR','TMP',
             'relative path for temp files below FILES_DIR'),
        ('PATHS','WDUX_ROOT','/home/watchdog/wdux',
             'path for root containing FILES_DIR'),
        ('PLATFORM','lastb_CMD','/usr/sbin/lastb -Rx',
             'command for listing failed logins'),
        ('PLATFORM','last_CMD','/usr/sbin/last -Rx',
             'command for listing successful logins'),
    ]

    missing = []
    reason = ['option "%(opt)s" in section "[%(sect)s]" missing',
              '"[%(sect)s]/%(opt)s" is empty']

    # read configuration file
    conf = wdlib.check_conf()
    if not conf:  # critical error
        return False
        

    for params in needed:
        sect,opt,val,desc = params
        if not conf.has_section(sect):  # section missing
            conf.add_section(sect)
        if conf.has_option(sect,opt):
            v = conf.get(sect,opt)
            if not v:  # value missing
                idx = needed.index(params)
                missing.append((1,idx))
        else: # option missing
            idx = needed.index(params)
            missing.append((0,idx))

    if missing:
        print 'Mandatory options or values are missing from config file %s!' % confpath
        print 'Empty entries are created now, please fill in the values!'
        print 
        for r,idx in missing:
            sect,opt,val,desc = needed[idx]
            print 'error:          ' + (reason[r] % vars())
            print 'description:    %s' % desc
            print 'possible value: e.g. "%s"' % val
            print
            if not opt:
                conf.add_section(sect)
            else:
                conf.add(sect,opt,'')
        conf.save()
        return False
    return True                    # has_all_conf_options(confpath)


def create_folder_structure():
    '''Check necessary paths and files, create if missing.
    Delete old detail files to avoid report generation
    from stale data.
    '''
    conf = wdlib.check_conf()
    root = wdlib.joinpath(
        conf.get('PATHS','WDUX_ROOT'),
        conf.get('PATHS','FILES_DIR')
        )
    pl = conf.get('PATHS','tmp_dir')
    tmppath = wdlib.abspath(os.path.join(root,pl))
    if not wdlib.mkpaths(root,pl):
        err('wdux: cannot access temp path "%s"! Aborted.\n' % tmppath)
        return False

    # create the daily archive folder for output files and report
    arch_root = conf.get('OUTPUT','arch_root')
    win_root = conf.get('OUTPUT','win_root')
    today = wdlib.datestr(wdlib._curserial,conf.get('OUTPUT','arch_fmt'))
    conf.add('CURRENT RUN','TODAY',today)

    dailyfmt = conf.get('OUTPUT','DAILY_DIR_FMT')   # '1-MON'
    # January 1 2001 was a Monday.
    pl = [datetime.date(2001,1,i+1).strftime(dailyfmt) for i in range(7)]
    pl.append(today)

    # delete the daily dir only (with detail files and report)
    # if the root dirs do not (yet) exist, do nothing
    wdlib.clearfolder(os.path.join(arch_root,today))
    wdlib.clearfolder(os.path.join(win_root,today))

    if not wdlib.mkpaths(arch_root,pl):
        err('wdux: cannot create path to ARCHIVE "%s"! Aborted.\n' % arch_root)
        return False
    # same folder tree under windows(-format) root
    if not wdlib.mkpaths(win_root,pl):
        err('wdux: cannot create path to WIN files "%s"! Aborted.\n' % win_root)
        return False

    # output path is fetched from the config file
    # instead of being constructed every time when needed
    # so that the hierarchy logic remains local
    p = wdlib.abspath(os.path.join(arch_root,today))
    conf.add('CURRENT RUN', 'OUTPATH', p)
    conf.add('CURRENT RUN', 'TMPPATH', tmppath)
    conf.save()
    return True  # create_folder_structure()


def cleanup(failed=True):
    ''' log status, restore stdout if neccessary
        if failed: abort
    '''
    
    # log status at end of processing
    wdlib.log_status('daily_run',is_OK=not failed)

    wdlib.info('')

    # restore output if redirected
    wdlib.redirect_stdout('')
    
    sys.exit(not failed)


def get_clusterstatus():
    '''Get cluster status of specified package using pipe.'''

    global cl_pkg, cl_sts
    
    conf = wdlib.check_conf()

    cl_pkg = conf.get('CLUSTER','cluster_package') or 'p1'
    cmd = conf.get('CLUSTER','cluster_cmd')
    cmd = cmd + ' ' + cl_pkg
    child_in, child_out, child_err = os.popen3(cmd)
    cl_sts = 'unknown'
    # returns e.g.:
    #    p1             up           running      enabled      hucuit36
    for line in child_out.readlines():
        L = line.strip().lower().split()
        if L:
            if L[0] == cl_pkg.lower():
                cl_sts = L[1]
                break
    child_in.close()
    child_out.close()
    child_err.close()


def main():
    ''' Prepare the folder structure, call scanning modules
    and create report, make copies, mail report.'''

    # ----------------
    # process command line
    # all options except 'help' handled later
    # 'help' will display usage and exit silently

    # when adding modules, modify list modules[] below!

    usage = __doc__ + '\nusage: %prog [options] file(s), -h for help on options'
    p = optparse.OptionParser(usage=usage)
    add = p.add_option  # =a shortcut
    add('-s', '--syslog', action='store_true',dest='opt_s',
              default=False, help='scan syslog.log ONLY')
    add('-c', '--consolelog', action='store_true',dest='opt_c',
              default=False, help='scan console.log ONLY')
    add('-l', '--last', action='store_true',dest='opt_l',
              default=False, help='scan login records ONLY')
    add('-p', '--passwd', action='store_true', dest='opt_p',
              default=False, help='scan /etc/passwd ONLY')
    add('-!', '--all', action='store_false', dest='filterOnTime',
              default=True, help='do NOT filter on timestamp')
    add('-v', '--verbose', action='store_true', dest='verbose',
              default=False, help='enable some more info on stderr')
    add('-o', '--output', action='store',dest='file',
              default='', type='string', help='redirect output to FILE')
    add('-f', '--conf', action='store',dest='confpath',
              default='', type='string', help='use as configuration file')
    add('-D', '--DEBUG', action='store_true', dest='DEBUG',
              default=False, help='enable debug msgs')

    # parse command line
    (options, args) = p.parse_args()

    # ----------------
    if options.verbose:
        wdlib.verbose = True
    else:
        # if stderr is redirected, verbose if False
        try:
            wdlib.verbose = sys.stderr.isatty()
        except AttributeError:
            pass  # leave it at False

    debugging = options.DEBUG

    # ----------------
    # process run_module boolean options
    modules  = [
            (scan_syslog.main,     options.opt_s),
            (scan_consolelog.main, options.opt_c),
            (scan_last.main,       options.opt_l),
            (check_passwd.main,    options.opt_p),
        ]
    # default action w/o run_options is to run all scans
    mods = [m[0] for m in modules if m[1]]
    # if all switches are False, mods is now empty;
    # that means to run them all:
    if not mods:
        mods = [m[0] for m in modules]
        
    # ----------------
    # determine the configuration file path (path + filename)
    # MANDATORY! or processing will be aborted soon.
    # if empty, some default will be used, see wdlib.py
    # returns the current valid confpath
    confpath = wdlib.set_confpath(options.confpath)
    
    # ----------------
    # check config file <confpath> for existence
    if not os.path.isfile(confpath) or not wdlib.check_conf():
        err('\n\n')
        err('%s\n' % sep)
        err('%s\n' % __version__)
        err('    WDUX configuration file is missing!\n')
        err('    specified: %s\n' % (confpath))
        err('    Aborted.\n')
        err('%s\n' % sep)
        err('\n\n')
        sys.exit(1)

    # ----------------
    # convert conf file
    convert_conf()

    # ----------------
    # check all folders and create if missing
    if not create_folder_structure():
        cleanup()

    # check mandatory conf options
    if not has_all_conf_options(confpath):
        sys.exit(1)

    # ----------------
    # get cluster status
    get_clusterstatus()
    
    # ----------------
    # for the operator
    if wdlib.verbose:
        wdux_header(confpath)
        print_overview(mods,wdlib.verbose)

    # ----------------
    # set or get the reportname
    reportname = options.file or get_reportname()

    # ----------------
    # from here on, all print statements print to file <reportname>
    # sys.stderr still goes to sys.stderr
    if not debugging:
        if not wdlib.redirect_stdout(reportname):
            err('wdux: cannot redirect output to report file "%s"! Aborted.\n' % reportname)
            sys.exit(1)

    # ----------------
    # here: for the report
    wdux_header(confpath)
    print_overview(mods,verbose=True)

    # ----------------
    # run the modules
    for module in mods:
        module(options.filterOnTime)

    # ----------------
    wdux_endheader()

    # ----------------
    # undo redirection; otherwise os.system() call fails!
    if not debugging:
        wdlib.redirect_stdout('')

    # ----------------
    # duplicate the files
    # this doesn't make sense if the filename is specified for this run
    if not options.file and not debugging:
        make_copies(reportname)

    # ----------------
    # mail the report
    if wdlib.verbose:
        wdlib.info('hint: mail is not sent if verbose or stderr is not redirected!')
    else:
        sendmail(reportname)

    # ----------------
    # done
    cleanup(failed=False)  # successful exit


if __name__ == '__main__':
    main()
