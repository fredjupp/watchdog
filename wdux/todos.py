#!/usr/bin/python
# -*- coding: iso-8859-1 -*-

'''
    module name: todos.py
    purpose    : convert files from UNIX to DOS style linefeeds
    created    : 2006-08-21
    last change: 2007-08-10
    
    by E/S/P Dr. Beneicke, Heidelberg
'''

import sys, os, os.path
import glob                      # handles wildcards in filenames
import optparse


# globals
err = sys.stderr.write
# replacements for routines in wdlib:
info = err
openfile = open
createfile = open


def convEOL(filename, toDOS=True, destdir='', DOSext='',noaction=False):
    '''Convert text file line ends between DOS and UNIX.
    Keeps file mode, access and modify time stamps.
    if <DOSext>: appends DOSext if toDOS, removes if toUNIX
    <noaction>: run without creating output
    '''
    import stat, os

    try:
        stbuf = os.stat(filename)
    except:
        stbuf = None

    fIN = openfile(filename,'rb')
    if not fIN:
        info('convEOL: cannot open %s for input' % filename)
        return False

    if toDOS:
        _from, _to = '\n', '\r\n'
        dd = 'toDOS'
    else:
        _from, _to = '\r\n', '\n'
        dd = 'toUNIX'
    destdir = destdir or dd   # default or specified

    newdata = fIN.read()
    fIN.close()
    if '\0' in newdata:
        info('convEOL: %-20s: binary!' % filename)
        return False

    # to DOS: do not convert if already in DOS mode!!
    if not (toDOS and '\r\n' in newdata):
        newdata = newdata.replace(_from, _to)

    # mkdir destination dir
    p, fname  = os.path.split(filename)
    if not os.path.exists(destdir):
        try:
            os.mkdir(destdir)
        except OSError,msg:
            err('convEOL:\n%s\n' % msg)
            return False

    # write to file
    fname = os.path.join(destdir,fname)
    if DOSext:    # handle extension
        if not DOSext.startswith('.'):
            DOSext = '.' + DOSext

        fn, ext = os.path.splitext(fname)
        if toDOS:
            if ext != DOSext:
                fname += DOSext
        else:
            if ext == DOSext:
                fname = fn

    if not noaction:
        fout = createfile(fname,'wb')
        if not fout:
            info('convEOL: cannot open %s for output' % fname)  # debug
            return False
        fout.write(newdata)
        fout.close()

        # copy mode, access and modify times
        if stbuf:
            try:
                os.chmod(fname,(stbuf[stat.ST_MODE]))
                os.utime(fname,(stbuf[stat.ST_ATIME],stbuf[stat.ST_MTIME]))
            except OSError:
                info('convEOL: error changing file times on %s!' % fname) # debug

    return True  # convEOL()


def UNIX2DOS(filename):
    ''' converts text file with CR+LF line ends to LF only
        keeps file mode, access and modify time stamps
    '''
    return convEOL(filename, toUNIX=True)


def DOS2UNIX(filename):
    ''' converts text file with LF only line ends to CR+LF
        keeps file mode, access and modify time stamps
    '''
    return convEOL(filename, toUNIX=False)



def main():
    '''Process command line, all options except 'help' handled later.
    'help' will display usage and exit silently.'''
    usage = __doc__ + '\n' + 'usage: %prog [options]'

    parser = optparse.OptionParser(usage=usage)

    parser.add_option('-r', '--recurse', action='store_true', dest='recurse',
                      default=False, help='recurse into directory tree')
    parser.add_option('-n', '--noaction', action='store_true', dest='noaction',
                      default=False, help='just show files, do not process')
    parser.add_option('-u', '--unix', action='store_true', dest='toUNIX',
                      default=False, help='convert to UNIX line ends')

    # parse command line
    (options, args) = parser.parse_args()

    # ----------------

    for arg in args:
        for f in glob.glob(arg):
            if os.path.exists(f) and os.path.isfile(f):         
                if convEOL(f, toDOS = not options.toUNIX,noaction=options.noaction):
                    print '+ ' + f
                else:
                    print '- ' + f


if __name__ == "__main__":
    main()
