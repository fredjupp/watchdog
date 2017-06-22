#!/usr/bin/python 
# -*- coding: iso-8859-1 -*-

''' -----------------------------------------------------
    WatchDog UX module

    module name: confparserlib.py
    purpose    : handling INI file
    created    : 2006-07-10
    last change: 2007-08-08

    for QVC Germany, Hueckelhoven
    by B+B Unternehmensberatung, Bad Duerkheim
    by E/S/P Dr. Beneicke, Heidelberg    
    -----------------------------------------------------
'''
''' history:
    2006-08-24
        initial release
    2006-08-28
        add: _read(): '~' in option values will be expanded to user's home dir
    2007-08-08
        chg: global variable __file__ sometimes undefined; wrapped

'''


"""Configuration file parser.

A setup file consists of sections, lead by a "[section]" header,
and followed by "name: value" entries, with continuations and such in
the style of RFC 822.

Intrinsic defaults can be specified by passing them into the
ConfigParser constructor as a dictionary.

class:

RawConfigParser -- responsible for parsing a list of
                   configuration files, and managing the parsed database.

    data structures:
    self._sections[section][option]=value  (dict of dicts of string)
    self._defaults[option] = value         (dict of string)

    methods:

    __init__(defaults=None)
        create the parser and specify a dictionary of intrinsic defaults.  The
        keys must be strings.  Note that `__name__' is always an intrinsic
        default; its value is the section's name.

    sections()
        return all the configuration section names, sans DEFAULT

    has_section(section)
        return whether the given section exists

    has_option(section, option)
        return whether the given option exists in the given section

    options(section)
        return list of configuration options for the named section

    read(filenames)
        read and parse the list of named configuration files, given by
        name.  A single filename is also allowed.  Non-existing files
        are ignored.  Return list of successfully read files.

    readfp(fp, filename=None)
        read and parse one configuration file, given as a file object.
        The filename defaults to fp.name; it is only used in error
        messages (if fp has no `name' attribute, the string `<???>' is used).

    get(section, option)
        return a string value for the named option.

    getint(section, options)
        like get(), but convert value to an integer

    getfloat(section, options)
        like get(), but convert value to a float

    getboolean(section, options)
        like get(), but convert value to a boolean (currently case
        insensitively defined as 0, false, no, off for False, and 1, true,
        yes, on for True).  Returns False or True.

    items(section)
        return a list of tuples with (name, value) for each option
        in the section.

    remove_section(section)
        remove the given file section and all its options

    remove_option(section, option)
        remove the given option from the given section

    set(section, option, value)
        set the given option

    write(fp)
        write the configuration state in .ini format
"""

import re, os.path
from time import strftime, localtime
from os.path import getmtime

# globals
try:
    test = __file__
except NameError:
    import sys
    __file__ = sys.argv[0]
__version__ = strftime('%Y-%m-%d %H:%M:%S',localtime(getmtime(__file__)))


__all__ = ["NoSectionError", "DuplicateSectionError", "NoOptionError",
           "ParsingError", "MissingSectionHeaderError",
           "RawConfigParser", "DEFAULTSECT"
          ]

DEFAULTSECT = "DEFAULT"  # must be uppercase!
CMT = '##CMT##'


# exception classes
class Error(Exception):
    """Base class for ConfigParser exceptions."""

    def __init__(self, msg=''):
        self.message = msg
        Exception.__init__(self, msg)

    def __repr__(self):
        return self.message

    __str__ = __repr__

class NoSectionError(Error):
    """Raised when no section matches a requested option."""

    def __init__(self, section):
        Error.__init__(self, 'No section: %r' % (section,))
        self.section = section

class DuplicateSectionError(Error):
    """Raised when a section is multiply-created."""

    def __init__(self, section):
        Error.__init__(self, "Section %r already exists" % section)
        self.section = section

class NoOptionError(Error):
    """A requested option was not found."""

    def __init__(self, option, section):
        Error.__init__(self, "No option %r in section: %r" %
                       (option, section))
        self.option = option
        self.section = section

class ParsingError(Error):
    """Raised when a configuration file does not follow legal syntax."""

    def __init__(self, filename):
        Error.__init__(self, 'File contains parsing errors: %s' % filename)
        self.filename = filename
        self.errors = []

    def append(self, lineno, line):
        self.errors.append((lineno, line))
        self.message += '\n\t[line %2d]: %s' % (lineno, line)

class MissingSectionHeaderError(ParsingError):
    """Raised when a key-value pair is found before any section header."""

    def __init__(self, filename, lineno, line):
        Error.__init__(
            self,
            'File contains no section headers.\nfile: %s, line: %d\n%r' %
            (filename, lineno, line))
        self.filename = filename
        self.lineno = lineno
        self.line = line

##########################################################################
# parser classes

class RawConfigParser:
    def __init__(self, defaults=None):
        self._sections = {}  # sect: ( sectionname, sect_comment, options dict )
                             # option dict: { opt: (optname,opt_cmt,optvalue), ...}

        # preset [DEFAULT] section dict
        self._defaults = {}  # (optname: value)

        if defaults:
            for option, value in defaults.items():
                opt = option.upper() # xform
                self._defaults[opt] = value

    def defaults(self):
        return self._defaults

    def sections(self):
        """Return a list of section names, excluding [DEFAULT]"""
        # self._sections will never have [DEFAULT] in it
        # E/S/P: return sorted keys
        ss = self._sections.keys()
        ss.sort()
        return ss

    def add_section(self, section):
        """Create a new section in the configuration.
        create a new dict accessed by _sections[section]
        raise DuplicateSectionError if a section by the specified name
        already exists.
        """
        sect = section.upper() # xform
        if sect in self._sections:
            raise DuplicateSectionError(section)
        self._sections[sect] = (section,'',{})  # name, comment, options dict
        
    def has_section(self, section):
        """Indicate whether the named section is present in the configuration.
           The DEFAULT section is not acknowledged.
        """
        return section.upper() in self._sections  # xform

    def options(self, section):
        """Return a list of option names for the given section name."""
        sect = section.upper() # xform
        if not sect in self._sections:
            raise NoSectionError(section)
            
        opts = self._sections[sect][2].copy()
        opts.update(self._defaults)
        if '__NAME__' in opts:
            del opts['__NAME__']
            
        # E/S/P: return sorted keys
        so = opts.keys()
        so.sort()
        return [opts[i][0] for i in so] # (name,cmt,value)


    def read(self, filenames):
        """Read and parse a filename or a list of filenames.

        Files that cannot be opened are silently ignored; this is
        designed so that you can specify a list of potential
        configuration file locations (e.g. current directory, user's
        home directory, systemwide directory), and all existing
        configuration files in the list will be read. A single
        filename may also be given.

        Return list of successfully read files.
        """
        if isinstance(filenames, basestring):
            filenames = [filenames]
        read_ok = []
        for filename in filenames:
            try:
                fp = open(filename)
            except IOError:
                continue
            # self._read(): Parse a sectioned setup file.
            self._read(fp, filename)
            fp.close()
            read_ok.append(filename)
        return read_ok


    def readfp(self, fp, filename=None):
        """Like read() but the argument must be a file-like object.

        The `fp' argument must have a `readline' method.  Optional
        second argument is the `filename', which if not given, is
        taken from fp.name.  If fp has no `name' attribute, `<???>' is
        used.
        """
        if filename is None:
            try:
                filename = fp.name
            except AttributeError:
                filename = '<???>'
        self._read(fp, filename)


    # E/S/P: from ConfigParser.get() without interpolation
    def get(self, section, option):
        """Get an option value for a given section.
        The section DEFAULT is special.
        """
        opt = option.upper()     # xform
        sect = section.upper()   # xform

        d = self._defaults.copy()
        try:
            d.update(self._sections[sect][2]) # current value overrides default
        except KeyError:
            if sect != DEFAULTSECT:
                raise NoSectionError(section)

        try:
            value = d[opt][2]
        except KeyError:
            raise NoOptionError(option, section)
        return value

        
    def _get(self, section, conv, option):
        return conv(self.get(section, option))

    def getint(self, section, option):
        return self._get(section, int, option)

    def getfloat(self, section, option):
        return self._get(section, float, option)

    # dict keys must be lowercase!
    _boolean_states = {'1': True, 'yes': True, 'true': True, 'on': True,
                       '0': False, 'no': False, 'false': False, 'off': False}

    def getboolean(self, section, option):
        v = self.get(section, option).lower()
        if v not in self._boolean_states:
            raise ValueError, 'Not a boolean: %s' % v
        return self._boolean_states[v]


    # E/S/P: from ConfigParser.items() w/o interpolation
    def items(self, section):
        """Return a list of tuples with (name, value) for each option
        in the specified section.
        The section DEFAULT is special.
        """

        sect = section.upper() # xform

        d = self._defaults.copy()
        try:
            d.update(self._sections[sect][2]) # current value overrides default
        except KeyError:
            if sect != DEFAULTSECT:
                raise NoSectionError(section)
        # Update with the entry specific variables
        options = d.keys()
        options.sort()  # E/S/P
        # d[option] is (name,cmt,value)
        # return original option string, not xform'ed key value
        return [ (d[opt][0],d[opt][2]) for opt in options ]

    
    def has_option(self, section, option):
        """Check for the existence of a given option in a given section."""
        opt = option.upper()
        sect = section.upper()
        if not section or sect == DEFAULTSECT:
            return opt in self._defaults
        elif sect not in self._sections:
            return False
        else:
            return (   opt in self._sections[sect][2]
                    or opt in self._defaults)

    def set(self, section, option, value):
        """ Set an option.
            Non-existant option will be added silently.
        """

         # added E/S/P: type check
        if not isinstance(value, basestring):
            raise TypeError("option values must be strings")

        opt = option.upper()
        sect = section.upper()
        
        if not sect or sect == DEFAULTSECT:
            self._defaults[opt] = value
        else:
            try:
                sectdict = self._sections[sect]
            except KeyError:
                raise NoSectionError(section)
            sectdict[2][opt] = (option,'',value)  # (name,cmt,value)


    def write(self, fp):
        """Write the configuration state to a conf-file."""

        # write all-line comments in a block at the beginning
        scmts = self._sections[CMT][2]
        if scmts:  # (name,cmt,value)
            # sort by original line no
            sc = scmts.keys()
            sc.sort()
            for cmt in sc:
                fp.write('%s\n' % (scmts[cmt][2]))
            fp.write('\n')

        if self._defaults:
            fp.write("[%s]\n" % DEFAULTSECT) 
            # sort before writing
            so = self._defaults.items()
            so.sort()
            for (option, value) in so:
                fp.write( "%s = %s  # default" % (option, value) )
                fp.write("\n")
            fp.write("\n")

        ss = self._sections.keys()
        ss.sort()
        for sect in ss:
            if sect == CMT or sect == DEFAULTSECT:
                continue
            s = self._sections[sect]      # (name,cmt,dict)
            if s[1]:
                fp.write('[%s] %s\n' % (s[0],s[1]))
            else:
                fp.write('[%s]\n' % (s[0]))

            if s[2]:
                ko = s[2].items()
                ko.sort()
                for key, o in ko:
                    if key != "__NAME__":
                        cmt = o[1]
                        if cmt:
                            fp.write('%-16s = %s   %s' % (o[0],o[2],cmt))
                        else:
                            fp.write('%-16s = %s' % (o[0],o[2])) # aligned
                            
                        fp.write('\n')
            fp.write("\n") # end of section


    def remove_option(self, section, option):
        """Remove an option."""
        
        opt = option.upper()
        sect = section.upper()
        if not sect or sect == DEFAULTSECT:
            sectdict = self._defaults
        else:
            if not sect in self._sections:
                raise NoSectionError(section)
            sectdict = self._sections[sect][2]

        existed = opt in sectdict
        if existed:
            del sectdict[opt]
        return existed


    def remove_section(self, section):
        """Remove a section."""
        sect = section.upper()
        existed = sect in self._sections
        if existed:
            del self._sections[sect]
        return existed



    def _read(self, fp, fpname):
        """Parse a sectioned setup file.

        The sections in setup file contain a title line at the top,
        indicated by a name in square brackets ('[]'), plus key/value
        options lines, indicated by 'name = value' format lines.
        Continuations are represented by an embedded newline then
        leading whitespace.  Blank lines, lines beginning with a '#',
        and just about everything else are ignored.
        """
        #
        # Regular expressions for parsing section headers and options.
        #

        a_section = r'''
            (?ix)                       # ignore case, allow verbose
            ^\[                         # [ at BOL
            (?P<section>[^]#]+)         # non-empty, no cmt sign
            \]                          # ]
            \s*                         # opt. white space
            ((?P<sectcmt>[#].*))?$      # opt. #+<sectcmt> up to EOL
            '''
        an_option = r'''
            (?ix)                       # ignore case, allow verbose
            ^(?P<option>[^:=]+?)        # non-empty, not greedy
            \s*                         # opt. white space
            (?P<vi>[:=])                # separator 'vi'(either : or =)
            \s*                         # opt. white space
            (?P<value>[^#]+?)??         # non-empty, not greedy
            \s*?                        # opt. white space
            ((?P<optcmt>[#].*))?$       # opt. #+<optcmt> up to EOL
            '''
        a_comment = r'''           
            (?ix)                       # ignore case, allow verbose
            ^(?P<cmt>[#].*?)\s*$        # comment sign and up to trailing wsp
            '''

        cREstr = a_comment + '|' + a_section + '|' + an_option 
        cRE = re.compile(cREstr)        
        
        cursect = None                            # None, or a dictionary
        optname = opt = None
        lineno = 0
        e = None                                  # None, or an exception
        ncmt = 0
        SectRead = False                          # a once-only flag
        for line in fp:
            lineno += 1
            line = line.strip()
            if not line:         #  skip blank lines
                continue
            mo = cRE.match(line)
            if not mo:
                continue
            
            gd = mo.groupdict()
            section = gd['section']
            sectcmt = gd['sectcmt']
            option  = gd['option']
            value   = gd['value']
            optcmt  = gd['optcmt']
            cmt     = gd['cmt']
            # comment?
            if cmt:  # standalone comment
                if SectRead:
                    continue  # comments after first section header are ignored
                # add a CMT section in sections dict if not present
                if not CMT in self._sections:
                    self._sections[CMT] = (CMT,'',{})
                # key is current comment no.
                ncmt += 1
                n = 'CMT_%.4d' % ncmt
                self._sections[CMT][2][n] = (n,'',cmt)
              #  continue      # ... and skip
            
            # a section?
            elif section:
                sect = section.upper() # xform
                if sect in self._sections:
                    cursect = self._sections[sect][2]
                elif sect == DEFAULTSECT:
                    cursect = self._defaults
                else:  # create new section '[section]'
                    self._sections[sect] = (section,sectcmt,{})  # (name,cmt,dict)
                    cursect = self._sections[sect][2]

                SectRead = True                    
            # an option?
            elif option:
                # no section header in the file?
                if cursect is None:                    
                    raise MissingSectionHeaderError(fpname, lineno, line)
                
                # allow empty values, either ="" or nothing at all
                if not value or value == '""':
                    value = ''
                option = option.strip()
                
                # add-on 2006-08-28
                # if value contains a tilde, assume it is a path
                # try to expand to user's home dir or leave it unchanged
                if '~' in value:
                    value = os.path.expanduser(value)
                    
                opt = option.upper()     # xform
                cursect[opt] = (option,optcmt,value) # (name,cmt,value)
            else:
                # a non-fatal parsing error occurred.  set up the
                # exception but keep going. the exception will be
                # raised at the end of the file and will contain a
                # list of all bogus lines
                if not e:
                    e = ParsingError(fpname)
                e.append(lineno, repr(line))
        # if any parsing errors occurred, raise an exception
        if e:
            raise e


# -----------------------------------------------------
if __name__ == "__main__":
    import wdlib
    print wdlib.myversion(__file__)
