#@+leo-ver=5-thin
#@+node:ekr.20100208065621.5894: * @file leoCache.py
'''A module encapsulating Leo's file caching'''
#@+<< imports >>
#@+node:ekr.20100208223942.10436: ** << imports >> (leoCache)
import sys
isPython3 = sys.version_info >= (3, 0, 0)
import leo.core.leoGlobals as g
###import leo.core.leoNodes as leoNodes
if isPython3:
    import pickle
else:
    import cPickle as pickle
# import glob
import fnmatch
import hashlib
import os
import stat
# import time
import zlib
import sqlite3
# try:
    # import marshal
# except ImportError:
    # marshal = None
#@-<< imports >>
# Abbreviations used throughout.
abspath = g.os_path_abspath
basename = g.os_path_basename
expanduser = g.os_path_expanduser
isdir = g.os_path_isdir
isfile = g.os_path_isfile
join = g.os_path_join
normcase = g.os_path_normcase
split = g.os_path_split
SQLITE = True
#@+others
#@+node:ekr.20100208062523.5885: ** class Cacher
class Cacher(object):
    '''A class that encapsulates all aspects of Leo's file caching.'''
    #@+others
    #@+node:ekr.20100208082353.5919: *3* cacher.Birth
    #@+node:ekr.20100208062523.5886: *4* cacher.ctor
    def __init__(self, c=None):
        
        self.c = c
        # set by initFileDB and initGlobalDB...
        self.db = {}
            # When caching is enabled will be a PickleShareDB instance.
        self.dbdirname = None # A string.
        self.globals_tag = 'leo.globals'
            # 'leo3k.globals' if g.isPython3 else 'leo2k.globals'
        self.inited = False
    #@+node:ekr.20100208082353.5918: *4* cacher.initFileDB
    def initFileDB(self, fn):

        if not fn:
            return
        pth, bname = split(fn)
        if pth and bname:
            sfn = g.shortFileName(fn) # For dumps.
            fn = fn.lower()
            fn = g.toEncodedString(fn) # Required for Python 3.x.
            # Important: this creates a top-level directory of the form x_y.
            # x is a short file name, included for convenience.
            # y is a key computed by the *full* path name fn.
            # Thus, there will a separate top-level directory for every path.
            self.dbdirname = dbdirname = join(g.app.homeLeoDir, 'db',
                '%s_%s' % (bname, hashlib.md5(fn).hexdigest()))
            self.db = SqlitePickleShare(dbdirname) if SQLITE else PickleShareDB(dbdirname)
            # Fixes bug 670108.
            self.c.db = self.db
            self.inited = True
            self.dump(self.db, 'c.db: %s' % sfn)
    #@+node:ekr.20100208082353.5920: *4* cacher.initGlobalDb
    def initGlobalDB(self):
        '''
        g.app.doPrePluginsInit() calls this method to init g.app.db.
        
        Plugins and scripts can use this as follows:

            g.app.db['hello'] = [1,2,5]
            
        This method *always* creates .leo/db/global, even if caching is
        disabled.
        '''
        try:
            dbdirname = g.app.homeLeoDir + "/db/global"
            db = SqlitePickleShare(dbdirname) if SQLITE else PickleShareDB(dbdirname)
            self.db = db
            self.inited = True
            self.dump(self.db, 'g.app.db')
            return db
        except Exception:
            return {} # Use a plain dict as a dummy.
    #@+node:ekr.20100209160132.5759: *3* cacher.clearCache & clearAllCaches
    def clearCache(self):
        '''Clear the cache for the open window.'''
        if self.db:
            # Be careful about calling db.clear.
            try:
                self.db.clear(verbose=True)
            except TypeError:
                self.db.clear() # self.db is a Python dict.
            except Exception:
                g.trace('unexpected exception')
                g.es_exception()
                self.db = {}

    def clearAllCaches(self):
        '''
        Clear the Cachers *only* for all open windows. This is much safer than
        killing all db's.
        '''
        for frame in g.windows():
            c = frame.c
            if c.cacher:
                c.cacher.clearCache()
        g.es('done', color='blue')
    #@+node:ekr.20180611054447.1: *3* cacher.dump
    def dump(self, db, tag):
        '''Dump the indicated cache.'''
        
        def dump_list(aList, result, indent=0):
            head, body, gnx, children = tuple(aList)
            assert isinstance(children, list)
            result.append('%6s%s %20s %s' % (len(body), ' '*indent, gnx, head))
            for child in children:
                dump_list(child, result, indent=indent+2)

        if 'cache' not in g.app.debug:
            return
        print('\n===== %s =====\n' % tag)
        for key in db.keys():
            key = key[0]
            val = db.get(key)
            print('%s:' % key)
            if key.startswith('fcache/'):
                assert isinstance(val, list), val.__class__.__name__
                result = ['list of nodes...']
                dump_list(val, result)
                if 1: # Brief
                    n = len(result)-1
                    print('%s node%s in %s' % (n, g.plural(n), val[0].strip()))
                else:
                    g.printObj(result)
            elif g.isString(val):
                print(val)
            elif isinstance(val, (int, float)):
                print(val)
            else:
                g.printObj(val)
            print('')
    #@+node:ekr.20100208071151.5907: *3* cacher.fileKey
    def fileKey(self, fileName, content):
        '''
        Compute the hash of branch name, fileName and content.
        '''
        m = hashlib.md5()
        if 1:
            # Use only the contents.
            m.update(g.toEncodedString(content))
        else:
            branch = g.toEncodedString(g.gitBranchName())
            content = g.toEncodedString(content)
            fileName = g.toEncodedString(fileName)
            m.update(branch)
            m.update(fileName)
            m.update(content)
        return "fcache/" + m.hexdigest()
    #@+node:ekr.20180624041117.1: *3* cacher.Reading
    #@+node:ekr.20180624044526.1: *4* cacher.getGlobalData
    def getGlobalData(self, fn):
        '''Return a dict containing all global data.'''
        key = self.fileKey(fn, self.globals_tag)
        data = self.db.get('window_position_%s' % (key))
        if data:
            # pylint: disable=unpacking-non-sequence
            top, left, height, width = data
            d = {
                'top': int(top),
                'left': int(left),
                'height': int(height),
                'width': int(width),
            }
        # Return reasonable defaults.
        else:
            d = {'top': 50, 'left': 50, 'height': 500, 'width': 800}
        d['r1'] = float(self.db.get('body_outline_ratio_%s' % (key), '0.5'))
        d['r2'] = float(self.db.get('body_secondary_ratio_%s' % (key), '0.5'))
        return d
    #@+node:ekr.20100208082353.5924: *4* cacher.getCachedStringPosition
    def getCachedStringPosition(self, fn):

        key = self.fileKey(fn, self.globals_tag)
        str_pos = self.db.get('current_position_%s' % key)
        return str_pos
    #@+node:ekr.20100208082353.5927: *3* cacher.Writing
    #@+node:ekr.20100208071151.5901: *4* cacher.makeCacheList
    def makeCacheList(self, p):
        '''Create a recursive list describing a tree
        for use by createOutlineFromCacheList.
        '''
        # This is called after at.readPostPass, so p.b *is* the body text.
        return [
            p.h, p.b, p.gnx,
            [self.makeCacheList(p2) for p2 in p.children()]]
    #@+node:ekr.20100210163813.5747: *4* cacher.save
    def save(self, fn, changeName):
        ### g.trace('=====', fn)
        if SQLITE:
            self.commit(True)
        if changeName or not self.inited:
            self.initFileDB(fn)
    #@+node:ekr.20100208082353.5929: *4* cacher.setCachedGlobalsElement
    def setCachedGlobalsElement(self, fn):

        c = self.c
        key = self.fileKey(fn, self.globals_tag)
        self.db['body_outline_ratio_%s' % key] = str(c.frame.ratio)
        self.db['body_secondary_ratio_%s' % key] = str(c.frame.secondary_ratio)
        width, height, left, top = c.frame.get_window_info()
        self.db['window_position_%s' % key] = (
            str(top), str(left), str(height), str(width))
    #@+node:ekr.20100208082353.5928: *4* cacher.setCachedStringPosition
    def setCachedStringPosition(self, str_pos):

        c = self.c
        key = self.fileKey(c.mFileName, self.globals_tag)
        self.db['current_position_%s' % key] = str_pos
    #@+node:ekr.20100208065621.5890: *3* cacher.test
    def test(self):
        
        # pylint: disable=no-member
        if g.app.gui.guiName() == 'nullGui':
            # Null gui's don't normally set the g.app.gui.db.
            g.app.setGlobalDb()
        # Fixes bug 670108.
        assert g.app.db is not None
            # a PickleShareDB instance.
        # Make sure g.guessExternalEditor works.
        g.app.db.get("LEO_EDITOR")
        self.initFileDB('~/testpickleshare')
        db = self.db
        db.clear()
        assert not list(db.items())
        db['hello'] = 15
        db['aku ankka'] = [1, 2, 313]
        db['paths/nest/ok/keyname'] = [1, (5, 46)]
        db.uncache() # frees memory, causes re-reads later
        if 0: print(db.keys())
        db.clear()
        return True
    #@+node:ekr.20170624135447.1: *3* cacher.warning
    def warning(self, s):
        '''Print a warning message in red.'''
        g.es_print('Warning: %s' % s.lstrip(), color='red')
    #@-others
    def commit(self, close=True):
        # in some cases while unit testing self.db is python dict
        if SQLITE and hasattr(self.db, 'conn'):
            # pylint: disable=no-member
            self.db.conn.commit()
            if close:
                self.db.conn.close()
                self.inited = False
#@+node:ekr.20100208223942.5967: ** class PickleShareDB
_sentinel = object()

class PickleShareDB(object):
    """ The main 'connection' object for PickleShare database """
    #@+others
    #@+node:ekr.20100208223942.5968: *3*  Birth & special methods
    #@+node:ekr.20100208223942.5969: *4*  __init__ (PickleShareDB)
    def __init__(self, root):
        """
        Init the PickleShareDB class.
        root: The directory that contains the data. Created if it doesn't exist.
        """
        self.root = abspath(expanduser(root))
        if not isdir(self.root) and not g.unitTesting:
            self._makedirs(self.root)
        self.cache = {}
            # Keys are normalized file names.
            # Values are tuples (obj, orig_mod_time)

        def loadz(fileobj):
            if fileobj:
                try:
                    val = pickle.loads(
                        zlib.decompress(fileobj.read()))
                except ValueError:
                    g.es("Unpickling error - Python 3 data accessed from Python 2?")
                    return None
                return val
            else:
                return None

        def dumpz(val, fileobj):
            if fileobj:
                try:
                    # use Python 2's highest protocol, 2, if possible
                    data = pickle.dumps(val, 2)
                except Exception:
                    # but use best available if that doesn't work (unlikely)
                    data = pickle.dumps(val, pickle.HIGHEST_PROTOCOL)
                compressed = zlib.compress(data)
                fileobj.write(compressed)

        self.loader = loadz
        self.dumper = dumpz
    #@+node:ekr.20100208223942.5970: *4* __contains__(PickleShareDB)
    def __contains__(self, key):

        return self.has_key(key) # NOQA
    #@+node:ekr.20100208223942.5971: *4* __delitem__
    def __delitem__(self, key):
        """ del db["key"] """
        fn = join(self.root, key)
        self.cache.pop(fn, None)
        try:
            os.remove(fn)
        except OSError:
            # notfound and permission denied are ok - we
            # lost, the other process wins the conflict
            pass
    #@+node:ekr.20100208223942.5972: *4* __getitem__
    def __getitem__(self, key):
        """ db['key'] reading """
        fn = join(self.root, key)
        try:
            mtime = (os.stat(fn)[stat.ST_MTIME])
        except OSError:
            raise KeyError(key)
        if fn in self.cache and mtime == self.cache[fn][1]:
            obj = self.cache[fn][0]
            return obj
        try:
            # The cached item has expired, need to read
            obj = self.loader(self._openFile(fn, 'rb'))
        except Exception:
            raise KeyError(key)
        self.cache[fn] = (obj, mtime)
        return obj
    #@+node:ekr.20100208223942.5973: *4* __iter__
    def __iter__(self):

        for k in list(self.keys()):
            yield k
    #@+node:ekr.20100208223942.5974: *4* __repr__
    def __repr__(self):
        return "PickleShareDB('%s')" % self.root
    #@+node:ekr.20100208223942.5975: *4* __setitem__
    def __setitem__(self, key, value):
        """ db['key'] = 5 """
        fn = join(self.root, key)
        parent, junk = split(fn)
        if parent and not isdir(parent):
            self._makedirs(parent)
        self.dumper(value, self._openFile(fn, 'wb'))
        try:
            mtime = os.path.getmtime(fn)
            self.cache[fn] = (value, mtime)
        except OSError as e:
            if e.errno != 2:
                raise
    #@+node:ekr.20100208223942.10452: *3* _makedirs
    def _makedirs(self, fn, mode=0o777):

        os.makedirs(fn, mode)
    #@+node:ekr.20100208223942.10458: *3* _openFile
    def _openFile(self, fn, mode='r'):
        """ Open this file.  Return a file object.

        Do not print an error message.
        It is not an error for this to fail.
        """
        try:
            return open(fn, mode)
        except Exception:
            return None
    #@+node:ekr.20100208223942.10454: *3* _walkfiles & helpers
    def _walkfiles(self, s, pattern=None):
        """ D.walkfiles() -> iterator over files in D, recursively.

        The optional argument, pattern, limits the results to files
        with names that match the pattern.  For example,
        mydir.walkfiles('*.tmp') yields only files with the .tmp
        extension.
        """
        for child in self._listdir(s):
            if isfile(child):
                if pattern is None or self._fn_match(child, pattern):
                    yield child
            elif isdir(child):
                for f in self._walkfiles(child, pattern):
                    yield f
    #@+node:ekr.20100208223942.10456: *4* _listdir
    def _listdir(self, s, pattern=None):
        """ D.listdir() -> List of items in this directory.

        Use D.files() or D.dirs() instead if you want a listing
        of just files or just subdirectories.

        The elements of the list are path objects.

        With the optional 'pattern' argument, this only lists
        items whose names match the given pattern.
        """
        names = os.listdir(s)
        if pattern is not None:
            names = fnmatch.filter(names, pattern)
        return [join(s, child) for child in names]
    #@+node:ekr.20100208223942.10464: *4* _fn_match
    def _fn_match(self, s, pattern):
        """ Return True if self.name matches the given pattern.

        pattern - A filename pattern with wildcards, for example '*.py'.
        """
        return fnmatch.fnmatch(basename(s), pattern)
    #@+node:ekr.20100208223942.5978: *3* clear (PickleShareDB)
    def clear(self, verbose=False):
        # Deletes all files in the fcache subdirectory.
        # It would be more thorough to delete everything
        # below the root directory, but it's not necessary.
        if verbose:
            g.red('clearing cache at directory...\n')
            g.es_print(self.root)
        for z in self.keys():
            self.__delitem__(z)
    #@+node:ekr.20100208223942.5979: *3* get
    def get(self, key, default=None):

        try:
            val = self[key]
            return val
        except KeyError:
            return default
    #@+node:ekr.20100208223942.5980: *3* has_key (PickleShareDB)
    def has_key(self, key):

        try:
            self[key]
        except KeyError:
            return False
        return True
    #@+node:ekr.20100208223942.5981: *3* items
    def items(self):
        return [z for z in self]
    #@+node:ekr.20100208223942.5982: *3* keys & helpers (PickleShareDB)
    # Called by clear, and during unit testing.

    def keys(self, globpat=None):
        """Return all keys in DB, or all keys matching a glob"""
        if globpat is None:
            files = self._walkfiles(self.root)
        else:
            # Do not call g.glob_glob here.
            files = [z for z in join(self.root, globpat)]
        result = [self._normalized(p) for p in files if isfile(p)]
        return result
    #@+node:ekr.20100208223942.5976: *4* _normalized
    def _normalized(self, p):
        """ Make a key suitable for user's eyes """
        # os.path.relpath doesn't work here.
        return self._relpathto(self.root, p).replace('\\', '/')
    #@+node:ekr.20100208223942.10460: *4* _relpathto
    # Used only by _normalized.

    def _relpathto(self, src, dst):
        """ Return a relative path from self to dst.

        If there is no relative path from self to dst, for example if
        they reside on different drives in Windows, then this returns
        dst.abspath().
        """
        origin = abspath(src)
        dst = abspath(dst)
        orig_list = self._splitall(normcase(origin))
        # Don't normcase dst!  We want to preserve the case.
        dest_list = self._splitall(dst)
        if orig_list[0] != normcase(dest_list[0]):
            # Can't get here from there.
            return dst
        # Find the location where the two paths start to differ.
        i = 0
        for start_seg, dest_seg in zip(orig_list, dest_list):
            if start_seg != normcase(dest_seg):
                break
            i += 1
        # Now i is the point where the two paths diverge.
        # Need a certain number of "os.pardir"s to work up
        # from the origin to the point of divergence.
        segments = [os.pardir] * (len(orig_list) - i)
        # Need to add the diverging part of dest_list.
        segments += dest_list[i:]
        if segments:
            return join(*segments)
        else:
            # If they happen to be identical, use os.curdir.
            return os.curdir
    #@+node:ekr.20100208223942.10462: *4* _splitall
    # Used by relpathto.

    def _splitall(self, s):
        """ Return a list of the path components in this path.

        The first item in the list will be a path.  Its value will be
        either os.curdir, os.pardir, empty, or the root directory of
        this path (for example, '/' or 'C:\\').  The other items in
        the list will be strings.

        path.path.joinpath(*result) will yield the original path.
        """
        parts = []
        loc = s
        while loc != os.curdir and loc != os.pardir:
            prev = loc
            loc, child = split(prev)
            if loc == prev:
                break
            parts.append(child)
        parts.append(loc)
        parts.reverse()
        return parts
    #@+node:ekr.20100208223942.5989: *3* uncache
    def uncache(self, *items):
        """ Removes all, or specified items from cache

        Use this after reading a large amount of large objects
        to free up memory, when you won't be needing the objects
        for a while.

        """
        if not items:
            self.cache = {}
        for it in items:
            self.cache.pop(it, None)
    #@-others
#@+node:vitalije.20170716201700.1: ** class SqlitePickleShare
_sentinel = object()

class SqlitePickleShare(object):
    """ The main 'connection' object for SqlitePickleShare database """
    #@+others
    #@+node:vitalije.20170716201700.2: *3*  Birth & special methods
    def init_dbtables(self, conn):
        sql = 'create table if not exists cachevalues(key text primary key, data blob);'
        conn.execute(sql)
    #@+node:vitalije.20170716201700.3: *4*  __init__ (SqlitePickleShare)
    def __init__(self, root):
        """
        Init the SqlitePickleShare class.
        root: The directory that contains the data. Created if it doesn't exist.
        """
        self.root = abspath(expanduser(root))
        if not isdir(self.root) and not g.unitTesting:
            self._makedirs(self.root)
        dbfile = ':memory:' if g.unitTesting else join(root, 'cache.sqlite')
        self.conn = sqlite3.connect(dbfile, isolation_level=None)
        self.init_dbtables(self.conn)
        self.cache = {}
            # Keys are normalized file names.
            # Values are tuples (obj, orig_mod_time)

        def loadz(data):
            if data:
                try:
                    val = pickle.loads(zlib.decompress(data))
                except (ValueError, TypeError):
                    g.es("Unpickling error - Python 3 data accessed from Python 2?")
                    return None
                return val
            else:
                return None

        def dumpz(val):
            try:
                # use Python 2's highest protocol, 2, if possible
                data = pickle.dumps(val, protocol=2)
            except Exception:
                # but use best available if that doesn't work (unlikely)
                data = pickle.dumps(val, pickle.HIGHEST_PROTOCOL)
            return sqlite3.Binary(zlib.compress(data))

        self.loader = loadz
        self.dumper = dumpz
        if g.isPython3:
            self.reset_protocol_in_values()
    #@+node:vitalije.20170716201700.4: *4* __contains__(SqlitePickleShare)
    def __contains__(self, key):

        return self.has_key(key) # NOQA
    #@+node:vitalije.20170716201700.5: *4* __delitem__
    def __delitem__(self, key):
        """ del db["key"] """
        try:
            self.conn.execute('''delete from cachevalues
                where key=?''', (key,))
        except sqlite3.OperationalError:
            pass

    #@+node:vitalije.20170716201700.6: *4* __getitem__
    def __getitem__(self, key):
        """ db['key'] reading """
        try:
            obj = None
            for row in self.conn.execute('''select data from cachevalues
                where key=?''', (key,)):
                obj = self.loader(row[0])
                break
            else:
                raise KeyError(key)
        except sqlite3.Error:
            raise KeyError(key)
        return obj
    #@+node:vitalije.20170716201700.7: *4* __iter__
    def __iter__(self):

        for k in list(self.keys()):
            yield k
    #@+node:vitalije.20170716201700.8: *4* __repr__
    def __repr__(self):
        return "SqlitePickleShare('%s')" % self.root
    #@+node:vitalije.20170716201700.9: *4* __setitem__
    def __setitem__(self, key, value):
        """ db['key'] = 5 """
        try:
            data = self.dumper(value)
            self.conn.execute('''replace into cachevalues(key, data)
                values(?,?);''', (key, data))
        except sqlite3.OperationalError as e:
            g.es_exception(e)

    #@+node:vitalije.20170716201700.10: *3* _makedirs
    def _makedirs(self, fn, mode=0o777):

        os.makedirs(fn, mode)
    #@+node:vitalije.20170716201700.11: *3* _openFile
    def _openFile(self, fn, mode='r'):
        """ Open this file.  Return a file object.

        Do not print an error message.
        It is not an error for this to fail.
        """
        try:
            return open(fn, mode)
        except Exception:
            return None
    #@+node:vitalije.20170716201700.12: *3* _walkfiles & helpers
    def _walkfiles(self, s, pattern=None):
        """ D.walkfiles() -> iterator over files in D, recursively.

        The optional argument, pattern, limits the results to files
        with names that match the pattern.  For example,
        mydir.walkfiles('*.tmp') yields only files with the .tmp
        extension.
        """
        
    #@+node:vitalije.20170716201700.13: *4* _listdir
    def _listdir(self, s, pattern=None):
        """ D.listdir() -> List of items in this directory.

        Use D.files() or D.dirs() instead if you want a listing
        of just files or just subdirectories.

        The elements of the list are path objects.

        With the optional 'pattern' argument, this only lists
        items whose names match the given pattern.
        """
        names = os.listdir(s)
        if pattern is not None:
            names = fnmatch.filter(names, pattern)
        return [join(s, child) for child in names]
    #@+node:vitalije.20170716201700.14: *4* _fn_match
    def _fn_match(self, s, pattern):
        """ Return True if self.name matches the given pattern.

        pattern - A filename pattern with wildcards, for example '*.py'.
        """
        return fnmatch.fnmatch(basename(s), pattern)
    #@+node:vitalije.20170716201700.15: *3* clear (SqlitePickleShare)
    def clear(self, verbose=False):
        # Deletes all files in the fcache subdirectory.
        # It would be more thorough to delete everything
        # below the root directory, but it's not necessary.
        if verbose:
            g.red('clearing cache at directory...\n')
            g.es_print(self.root)
        self.conn.execute('delete from cachevalues;')
    #@+node:vitalije.20170716201700.16: *3* get
    def get(self, key, default=None):

        if not self.has_key(key):return default
        try:
            val = self[key]
            return val
        except KeyError:
            return default
    #@+node:vitalije.20170716201700.17: *3* has_key (PickleShareDB)
    def has_key(self, key):
        sql = 'select 1 from cachevalues where key=?;'
        for row in self.conn.execute(sql, (key,)):
            return True
        return False
    #@+node:vitalije.20170716201700.18: *3* items
    def items(self):
        sql = 'select key,data from cachevalues;'
        for key,data in self.conn.execute(sql):
            yield key, data
    #@+node:vitalije.20170716201700.19: *3* keys
    # Called by clear, and during unit testing.

    def keys(self, globpat=None):
        """Return all keys in DB, or all keys matching a glob"""
        if globpat is None:
            sql = 'select key from cachevalues;'
            args = tuple()
        else:
            sql = "select key from cachevalues where key glob ?;"
            # pylint: disable=trailing-comma-tuple
            args = globpat,
        for key in self.conn.execute(sql, args):
            yield key
    #@+node:vitalije.20170818091008.1: *3* reset_protocol_in_values
    def reset_protocol_in_values(self):
        PROTOCOLKEY = '__cache_pickle_protocol__'
        if self.get(PROTOCOLKEY, 3) == 2: return
        #@+others
        #@+node:vitalije.20170818115606.1: *4* viewrendered special case
        import json
        row = self.get('viewrendered_default_layouts') or (None, None)
        row = json.loads(json.dumps(row[0])), json.loads(json.dumps(row[1]))
        self['viewrendered_default_layouts'] = row
        #@+node:vitalije.20170818115617.1: *4* do_block
        def do_block(cur):
            itms = tuple((self.dumper(self.loader(v)), k) for k, v in cur)
            if itms:
                self.conn.executemany('update cachevalues set data=? where key=?', itms)
                self.conn.commit()
                return itms[-1][1]
            return None
        #@-others

        self.conn.isolation_level = 'DEFERRED'

        sql0 = '''select key, data from cachevalues order by key limit 50'''
        sql1 = '''select key, data from cachevalues where key > ? order by key limit 50'''


        block = self.conn.execute(sql0)
        lk = do_block(block)
        while lk:
            lk = do_block(self.conn.execute(sql1, (lk,)))
        self[PROTOCOLKEY] = 2
        self.conn.commit()

        self.conn.isolation_level = None
    #@+node:vitalije.20170716201700.23: *3* uncache
    def uncache(self, *items):
        """not used in SqlitePickleShare"""
        pass
    #@-others
#@-others
#@@language python
#@@tabwidth -4
#@@pagewidth 70
#@-leo
