#!/usr/bin/python 
# -*- coding: iso-8859-1 -*-
''' WatchDog/UX module
    
    module name: wdux_configfile.py
    purpose    : define Settings class representing a config file
    created    : 2006-07-10
    last change: 2007-08-08
    
    for QVC Germany, Hueckelhoven
    by B+B Unternehmensberatung, Bad Duerkheim
    by E/S/P Dr. Beneicke, Heidelberg
'''
''' history:
    2006-08-24
        initial release
    2006-08-28
        chg: save: call open(), not file()
    2006-08-29
        chg: save: keep last modified timestamp when writing
    2006-09-26
        chg: do not store OS to config file
        chg: store hostname to different conf section
    2007-07-30
        add: error handler for os.stat() calls in Settings.save()
    2007-08-08
        chg: global variable __file__ sometimes undefined; wrapped
'''


import sys 


# WDUX specific modules
from confparserlib import RawConfigParser 

# globals
from time import strftime, localtime
from os.path import getmtime

try:
    test = __file__
except NameError:
    import sys
    __file__ = sys.argv[0]

__version__ = strftime('%Y-%m-%d %H:%M:%S',localtime(getmtime(__file__)))

err = sys.stderr.write



class Settings(RawConfigParser):
    ''' Represents a config file as a dict.
    File is read, parsed and written on construction.'''
    
    _initial_settings = {}
    
    def __init__(self, filename, writedefaults = False):
        '''Read settings (option values) from INI file, update with default
        values and write back to file.

        <filename>: filename (path) to .INI config file
        <writedefaults>: do not write default values to the config file if FALSE
        A non-existing config file will ALWAYS be created.'''
        
        import platform

        
        RawConfigParser.__init__(self)
        
        self.filename = filename
        self.writedefaults = writedefaults
        
        # read settings from INI file
        # doesn't matter if it exists or not
        self.read(self.filename)
        
        # initialize from _initial_settings dict if asked for
        if self.writedefaults:
            for section,options in self._initial_settings.iteritems():
                if not self.has_section(section):
                    self.add_section(section)
                for option,value in options.iteritems():
                    if not self.has_option(section, option):
                        # i.e. will not override file content
                        self.set(section, option, value)

        # save hostname
        self.add('CURRENT RUN','host',platform.uname()[1].lower()) #[0]=OS, [1]=hostname
        self.save() # write/create INI file
        
    
    def save(self):
        '''Write conf file to disk but keep modified timestamp.'''

        import stat, os

        try:
            stbuf = os.stat(self.filename)
        except OSError:
            stbuf = None
            pass

        if stbuf:
            mtime = stbuf[stat.ST_MTIME]

        try:
            f = open(self.filename, "w")
        except IOError,msg:
            err('%s: cannot create: %r\n' % (self.filename, msg))
            pass
        else:
            self.write(f)   # instance method!
            f.close()

        # copy modify time
        try:
            stbuf = os.stat(self.filename)
        except OSError:
            stbuf = None
            pass
        if stbuf:
            try:
                os.utime(self.filename,(stbuf[stat.ST_ATIME],mtime))
            except OSError:
                pass


    def add(self, section, option, value):
        '''Add a value, create section and/or option if missing.'''
        if not self.has_section(section):
            self.add_section(section)
        self.set(section, option, value)
        

# -----------------------------------------------------
if __name__ == "__main__":
    import wdlib
    print wdlib.myversion(__file__)
