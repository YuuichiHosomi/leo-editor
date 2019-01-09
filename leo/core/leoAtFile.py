# -*- coding: utf-8 -*-
#@+leo-ver=5-thin
#@+node:ekr.20150323150718.1: * @file leoAtFile.py
#@@first
    # Needed because of unicode characters in tests.
"""Classes to read and write @file nodes."""
#@+<< imports >>
#@+node:ekr.20041005105605.2: ** << imports >> (leoAtFile)
import leo.core.leoGlobals as g
import leo.core.leoBeautify as leoBeautify
import leo.core.leoNodes as leoNodes
import os
import re
import sys
import time
#@-<< imports >>
#@+others
#@+node:ekr.20160514120655.1: ** class AtFile
class AtFile(object):
    """A class implementing the atFile subcommander."""
    #@+<< define class constants >>
    #@+node:ekr.20131224053735.16380: *3* << define class constants >>
    #@@nobeautify

    # directives...
    noDirective     =  1 # not an at-directive.
    allDirective    =  2 # at-all (4.2)
    docDirective    =  3 # @doc.
    atDirective     =  4 # @<space> or @<newline>
    codeDirective   =  5 # @code
    cDirective      =  6 # @c<space> or @c<newline>
    othersDirective =  7 # at-others
    miscDirective   =  8 # All other directives
    rawDirective    =  9 # @raw
    endRawDirective = 10 # @end_raw
    startVerbatim   = 11 # @verbatim
        # Not a real directive. Used to issue warnings.
    #@-<< define class constants >>
    #@+others
    #@+node:ekr.20041005105605.7: *3* at.Birth & init
    #@+node:ekr.20041005105605.8: *4* at.ctor & helpers
    # Note: g.getScript also call the at.__init__ and at.finishCreate().

    def __init__(self, c):
        '''ctor for atFile class.'''
        # **Warning**: all these ivars must **also** be inited in initCommonIvars.
        self.c = c
        self.encoding = 'utf-8' # 2014/08/13
        self.fileCommands = c.fileCommands
        self.errors = 0 # Make sure at.error() works even when not inited.
        # **Only** at.writeAll manages these flags.
        # promptForDangerousWrite sets cancelFlag and yesToAll only if canCancelFlag is True.
        self.canCancelFlag = False
        self.cancelFlag = False
        self.yesToAll = False
        # User options: set in reloadSettings.
        self.checkPythonCodeOnWrite = False
        self.runPyFlakesOnWrite = False
        self.underindentEscapeString = '\\-'
        self.reloadSettings()
    #@+node:ekr.20171113152939.1: *5* at.reloadSettings
    def reloadSettings(self):
        '''AtFile.reloadSettings'''
        c = self.c
        self.checkPythonCodeOnWrite = \
            c.config.getBool('check-python-code-on-write', default=True)
        self.runPyFlakesOnWrite = \
            c.config.getBool('run-pyflakes-on-write', default=False)
        self.underindentEscapeString = \
            c.config.getString('underindent-escape-string') or '\\-'
    #@+node:ekr.20150509194251.1: *4* at.cmd (decorator)
    def cmd(name):
        '''Command decorator for the AtFileCommands class.'''
        # pylint: disable=no-self-argument
        return g.new_cmd_decorator(name, ['c', 'atFileCommands',])
    #@+node:ekr.20041005105605.10: *4* at.initCommonIvars
    def initCommonIvars(self):
        """
        Init ivars common to both reading and writing.

        The defaults set here may be changed later.
        """
        at = self
        c = at.c
        at.at_auto_encoding = c.config.default_at_auto_file_encoding
        at.default_directory = None
        at.encoding = c.config.default_derived_file_encoding
        at.endSentinelComment = ""
        at.errors = 0
        at.inCode = True
        at.indent = 0 # The unit of indentation is spaces, not tabs.
        at.language = None
        at.output_newline = g.getOutputNewline(c=c)
        at.page_width = None
        at.pending = []
        at.raw = False # True: in @raw mode
        at.root = None # The root (a position) of tree being read or written.
        at.startSentinelComment = ""
        at.startSentinelComment = ""
        at.tab_width = c.tab_width or -4
        at.toString = False # True: sring-oriented read or write.
        at.writing_to_shadow_directory = False
    #@+node:ekr.20041005105605.13: *4* at.initReadIvars
    def initReadIvars(self, root, fileName,
        importFileName=None,
        perfectImportRoot=None,
        atShadow=False,
    ):
        at = self
        at.initCommonIvars()
        at.bom_encoding = None
            # The encoding implied by any BOM (set by g.stripBOM)
        at.cloneSibCount = 0
            # n > 1: Make sure n cloned sibs exists at next @+node sentinel
        at.correctedLines = 0
            # For perfect import.
        at.docOut = [] # The doc part being accumulated.
        at.done = False # True when @-leo seen.
        at.endSentinelIndentStack = []
            # Restored indentation for @-others and @-<< sentinels.
            # Used only when readVersion5.
        at.endSentinelStack = []
            # Contains entries for +node sentinels only when not readVersion5
        at.endSentinelLevelStack = []
            # The saved level, len(at.thinNodeStack), for @-others and @-<< sentinels.
            # Used only when readVersion5.
        at.endSentinelNodeStack = []
            # Used only when readVersion5.
        at.fromString = False
        at.importing = bool(importFileName)
        at.importRootSeen = False
        at.indentStack = []
        at.inputFile = None
        at.lastLines = [] # The lines after @-leo
        at.lastRefNode = None
            # The previous reference node, for at.readAfterRef.
            # No stack is needed because -<< sentinels restore at.v
            # to the node needed by at.readAfterRef.
        at.lastThinNode = None
            # The last thin node at this level.
            # Used by createThinChild4.
        at.leadingWs = ""
        at.lineNumber = 0 # New in Leo 4.4.8.
        at.out = None
        at.outStack = []
        at.perfectImportRoot = perfectImportRoot
        at.read_i = 0
        at.read_lines = []
        at.readVersion = ''
            # New in Leo 4.8: "4" or "5" for new-style thin files.
        at.readVersion5 = False
            # synonym for at.readVersion >= '5' and not atShadow.
        at.root = root
        at.rootSeen = False
        at.atShadow = atShadow
        at.targetFileName = fileName
        at.tnodeList = []
            # Needed until old-style @file nodes are no longer supported.
        at.tnodeListIndex = 0
        at.v = None
        at.vStack = [] # Stack of at.v values.
        at.thinChildIndexStack = [] # number of siblings at this level.
        at.thinFile = False
            # True if the external file uses new-style sentinels.
        at.thinNodeStack = [] # Entries are vnodes.
        at.updateWarningGiven = False
    #@+node:ekr.20041005105605.15: *4* at.initWriteIvars
    def initWriteIvars(self, root, targetFileName,
        atEdit=False,
        atShadow=False,
        forcePythonSentinels=False, # Was None
        nosentinels=False,
        toString=False,
    ):
        at, c = self, self.c
        assert root
        self.initCommonIvars()
        assert at.checkPythonCodeOnWrite is not None
        assert at.underindentEscapeString is not None
        at.atEdit = atEdit
        at.atShadow = atShadow
        # at.default_directory: set by scanAllDirectives()
        at.docKind = None
        if forcePythonSentinels:
            at.endSentinelComment = None
        # else: at.endSentinelComment set by initCommonIvars.
        # at.encoding: set by scanAllDirectives() below.
        # at.explicitLineEnding # True: an @lineending directive specifies the ending.
            # Set by scanAllDirectives() below.
        at.fileChangedFlag = False # True: the file has actually been updated.
        at.force_newlines_in_at_nosent_bodies = \
            c.config.getBool('force_newlines_in_at_nosent_bodies')
        # at.language:      set by scanAllDirectives() below.
        # at.outputFile:    set below.
        # at.outputNewline: set below.
        if forcePythonSentinels:
            # Force Python comment delims for g.getScript.
            at.startSentinelComment = "#"
        # else:                 set by initCommonIvars.
        # at.stringOutput:      set below.
        # at.outputFileName:    set below.
        # at.output_newline:    set by scanAllDirectives() below.
        # at.page_width:        set by scanAllDirectives() below.
        at.outputContents = None
        at.sameFiles = 0
        at.sentinels = not nosentinels
        at.shortFileName = "" # For messages.
        at.root = root
        # at.tab_width:         set by scanAllDirectives() below.
        at.targetFileName = targetFileName
            # Must be None for @shadow.
        at.thinFile = True
        at.toString = toString
        at.scanAllDirectives(root, forcePythonSentinels=forcePythonSentinels)
        # Sets the following ivars:
            # at.default_directory
            # at.encoding
            # at.explicitLineEnding
            # at.language
            # at.output_newline
            # at.page_width
            # at.tab_width
        # 2011/10/21: Encoding directive overrides everything else.
        if at.language == 'python':
            encoding = g.getPythonEncodingFromString(root.b)
            if encoding:
                at.encoding = encoding
        if toString:
            at.outputFile = g.FileLikeObject()
            if g.app.unitTesting:
                at.output_newline = '\n'
            # else: at.output_newline set in initCommonIvars.
            at.stringOutput = ""
            at.outputFileName = "<string-file>"
        else:
            # at.outputNewline set in initCommonIvars.
            at.outputFile = None
            at.stringOutput = None
            at.outputFileName = g.u('')
        # Init all other ivars even if there is an error.
        if not at.errors and at.root:
            if hasattr(at.root.v, 'tnodeList'):
                delattr(at.root.v, 'tnodeList')
            at.root.v._p_changed = True
    #@+node:ekr.20041005105605.17: *3* at.Reading
    #@+node:ekr.20041005105605.18: *4* at.Reading (top level)
    #@+node:ekr.20070919133659: *5* at.checkDerivedFile
    @cmd('check-derived-file')
    def checkDerivedFile(self, event=None):
        '''Make sure an external file written by Leo may be read properly.'''
        g.trace('=====')
        at = self; c = at.c; p = c.p
        if not p.isAtFileNode() and not p.isAtThinFileNode():
            return g.red('Please select an @thin or @file node')
        fn = p.anyAtFileNodeName()
        path = g.os_path_dirname(c.mFileName)
        fn = g.os_path_finalize_join(g.app.loadDir, path, fn)
        if not g.os_path_exists(fn):
            return g.error('file not found: %s' % (fn))
        s, e = g.readFileIntoString(fn)
        if s is None: return
        #
        # Create a dummy, unconnected, VNode as the root.
        root_v = leoNodes.VNode(context=c)
        root = leoNodes.Position(root_v)
        FastAtRead(c, gnx2vnode={}).read_into_root(s, fn, root)
        return c
    #@+node:ekr.20041005105605.19: *5* at.openFileForReading & helper
    def openFileForReading(self, fromString=False):
        '''
        Open the file given by at.root.
        This will be the private file for @shadow nodes.
        '''
        at, c = self, self.c
        if fromString:
            if at.atShadow:
                return at.error(
                    'can not call at.read from string for @shadow files')
            at.inputFile = g.FileLikeObject(fromString=fromString)
            at.initReadLine(fromString)
            return None, None
        #
        # Not from a string. Carefully read the file.
        fn = g.fullPath(c, at.root)
            # Returns full path, including file name.
        at.setPathUa(at.root, fn)
            # Remember the full path to this node.
        if at.atShadow:
            fn = at.openAtShadowFileForReading(fn)
            if not fn:
                return None, None
        assert fn
        try:
            # Open the file in binary mode to allow 0x1a in bodies & headlines.
            at.inputFile = open(fn, 'rb')
            s = at.readFileToUnicode(fn)
                # Sets at.encoding...
                #   From the BOM, if present.
                #   Otherwise from the header, if it has -encoding=
                #   Otherwise, uses existing value of at.encoding.
                # Then does:
                #    s = s.replace('\r\n','\n')
                #    at.initReadLine(s)
            at.warnOnReadOnlyFile(fn)
        except IOError:
            at.error("can not open: '@file %s'" % (fn))
            at.inputFile = None
            at._file_bytes = g.toEncodedString('')
            fn, s = None, None
        return fn, s
    #@+node:ekr.20150204165040.4: *6* at.openAtShadowFileForReading
    def openAtShadowFileForReading(self, fn):
        '''Open an @shadow for reading and return shadow_fn.'''
        at = self
        x = at.c.shadowController
        # readOneAtShadowNode should already have checked these.
        shadow_fn = x.shadowPathName(fn)
        shadow_exists = (g.os_path_exists(shadow_fn) and
            g.os_path_isfile(shadow_fn))
        if not shadow_exists:
            g.trace('can not happen: no private file',
                shadow_fn, g.callers())
            at.error('can not happen: private file does not exist: %s' % (
                shadow_fn))
            return None
        # This method is the gateway to the shadow algorithm.
        x.updatePublicAndPrivateFiles(at.root, fn, shadow_fn)
        return shadow_fn
    #@+node:ekr.20041005105605.21: *5* at.read & helpers
    def read(self, root, importFileName=None,
        fromString=None, atShadow=False, force=False
    ):
        """Read an @thin or @file tree."""
        at, c = self, self.c
        fileName = at.initFileName(fromString, importFileName, root)
        if not fileName:
            at.error("Missing file name.  Restoring @file tree from .leo file.")
            return False
        at.rememberReadPath(g.fullPath(c, root), root)
            # Fix bug 760531: always mark the root as read, even if there was an error.
            # Fix bug 889175: Remember the full fileName.
        at.initReadIvars(root, fileName,
            importFileName=importFileName, atShadow=atShadow)
        at.fromString = fromString
        if at.errors:
            return False
        fileName, file_s = at.openFileForReading(fromString=fromString)
            # For @shadow files, calls x.updatePublicAndPrivateFiles.
            # Calls at.initReadLine(s), where s is the file contents.
            # This will be used only if not cached.
        #
        # Set the time stamp.
        if fileName and at.inputFile:
            c.setFileTimeStamp(fileName)
        elif not fileName and not fromString and not file_s:
            return False
        root.clearVisitedInTree()
        at.scanAllDirectives(root, importing=at.importing, reading=True)
            # Sets the following ivars:
                # at.default_directory
                # at.encoding: **changed later** by readOpenFile/at.scanHeader.
                # at.explicitLineEnding
                # at.language
                # at.output_newline
                # at.page_width
                # at.tab_width
        gnx2vnode = c.fileCommands.gnxDict
        contents = fromString or file_s
        FastAtRead(c, gnx2vnode).read_into_root(contents, fileName, root)
        root.clearDirty()
        return True
    #@+node:ekr.20100122130101.6174: *6* at.deleteTnodeList
    def deleteTnodeList(self, p): # AtFile method.
        '''Remove p's tnodeList.'''
        v = p.v
        if hasattr(v, "tnodeList"):
            if False: # Not an error, but a useful trace.
                g.blue("deleting tnodeList for " + repr(v))
            delattr(v, "tnodeList")
            v._p_changed = True
    #@+node:ekr.20071105164407: *6* at.deleteUnvisitedNodes & helpers
    def deleteUnvisitedNodes(self, root, redraw=True):
        '''
        Delete unvisited nodes in root's subtree, not including root.

        Before Leo 5.6: Move unvisited node to be children of the 'Resurrected
        Nodes'.
        '''
        at = self
        # Find the unvisited nodes.
        aList = [z for z in root.subtree() if not z.isVisited()]
        if aList:
            # new-read: Never create resurrected nodes.
                # r = at.createResurrectedNodesNode()
                # callback = at.defineResurrectedNodeCallback(r, root)
                # # Move the nodes using the callback.
                # at.c.deletePositionsInList(aList, callback)
            at.c.deletePositionsInList(aList, redraw=redraw)
    #@+node:ekr.20100803073751.5817: *7* createResurrectedNodesNode
    def createResurrectedNodesNode(self):
        '''Create a 'Resurrected Nodes' node as the last top-level node.'''
        at = self; c = at.c; tag = 'Resurrected Nodes'
        # Find the last top-level node.
        last = c.rootPosition()
        while last.hasNext():
            last.moveToNext()
        # Create the node after last if it doesn't exist.
        if last.h == tag:
            p = last
        else:
            p = last.insertAfter()
            p.setHeadString(tag)
        p.expand()
        return p
    #@+node:ekr.20100803073751.5818: *7* defineResurrectedNodeCallback
    def defineResurrectedNodeCallback(self, r, root):
        '''Define a callback that moves node p as r's last child.'''

        def callback(p, r=r.copy(), root=root):
            '''The resurrected nodes callback.'''
            child = r.insertAsLastChild()
            child.h = 'From %s' % root.h
            v = p.v
            if 1: # new code: based on vnodes.
                import leo.core.leoNodes as leoNodes
                for parent_v in v.parents:
                    assert isinstance(parent_v, leoNodes.VNode), parent_v
                    if v in parent_v.children:
                        childIndex = parent_v.children.index(v)
                        v._cutLink(childIndex, parent_v)
                        v._addLink(len(child.v.children), child.v)
                    else:
                        # This would be surprising.
                        g.trace('**already deleted**', parent_v, v)
            else: # old code, based on positions.
                p.moveToLastChildOf(child)
            if not g.unitTesting:
                g.error('resurrected node:', v.h)
                g.blue('in file:', root.h)

        return callback
    #@+node:ekr.20041005105605.22: *6* at.initFileName
    def initFileName(self, fromString, importFileName, root):
        '''Return the fileName to be used in messages.'''
        at = self
        if fromString:
            fileName = "<string-file>"
        elif importFileName:
            fileName = importFileName
        elif root.isAnyAtFileNode():
            fileName = root.anyAtFileNodeName()
        else:
            fileName = None
        if fileName:
            # Fix bug 102: call the commander method, not the global funtion.
            fileName = at.c.os_path_finalize(fileName)
        return fileName
    #@+node:ekr.20100224050618.11547: *6* at.isFileLike
    def isFileLike(self, s):
        '''Return True if s has file-like sentinels.'''
        at = self; tag = "@+leo"
        s = g.toUnicode(s)
        i = s.find(tag)
        if i == -1:
            return True # Don't use the cache.
        else:
            j, k = g.getLine(s, i)
            line = s[j: k]
            valid, new_df, start, end, isThin = at.parseLeoSentinel(line)
            return not isThin
    #@+node:ekr.20041005105605.26: *5* at.readAll & helpers
    def readAll(self, root, force=False):
        """Scan positions, looking for @<file> nodes to read."""
        at, c = self, self.c
        old_changed = c.changed
        if force:
            # Capture the current headline only if
            # we aren't doing the initial read.
            c.endEditing()
        t1 = time.time()
        c.init_error_dialogs()
        files = at.findFilesToRead(force, root)
        for p in files:
            at.readFileAtPosition(force, p)
        for p in files:
            p.v.clearDirty()
        if not g.unitTesting:
            if files:
                t2 = time.time()
                g.es('read %s files in %2.2f seconds' % (len(files), t2 - t1))
            elif force:
                g.es("no @<file> nodes in the selected tree")
        c.changed = old_changed
        c.raise_error_dialogs()
    #@+node:ekr.20190108054317.1: *6* at.findFilesToRead
    def findFilesToRead(self, force, root):
        
        at, c = self, self.c
        p = root.copy()
        scanned_tnodes = set()
        files = []
        after = p.nodeAfterTree() if force else None
        while p and p != after:
            data = (p.gnx, g.fullPath(c, p))
            # skip clones referring to exactly the same paths.
            if data in scanned_tnodes:
                p.moveToNodeAfterTree()
                continue
            scanned_tnodes.add(data)
            if not p.h.startswith('@'):
                p.moveToThreadNext()
            elif p.isAtIgnoreNode():
                if p.isAnyAtFileNode():
                    c.ignored_at_file_nodes.append(p.h)
                p.moveToNodeAfterTree()
            elif p.isAtThinFileNode():
                at.read(p, force=force)
                files.append(p.copy())
                p.moveToNodeAfterTree()
            elif p.isAtAutoNode():
                fileName = p.atAutoNodeName()
                at.readOneAtAutoNode(fileName, p)
                files.append(p.copy())
                p.moveToNodeAfterTree()
            elif p.isAtEditNode():
                fileName = p.atEditNodeName()
                at.readOneAtEditNode(fileName, p)
                files.append(p.copy())
                p.moveToNodeAfterTree()
            elif p.isAtShadowFileNode():
                fileName = p.atShadowFileNodeName()
                at.readOneAtShadowNode(fileName, p)
                files.append(p.copy())
                p.moveToNodeAfterTree()
            elif p.isAtFileNode():
                at.read(p, force=force)
                files.append(p.copy())
                p.moveToNodeAfterTree()
            elif p.isAtAsisFileNode() or p.isAtNoSentFileNode():
                at.rememberReadPath(g.fullPath(c, p), p)
                p.moveToNodeAfterTree()
            elif p.isAtCleanNode():
                at.readOneAtCleanNode(p)
                files.append(p.copy())
                p.moveToThreadNext()
                    # #525: Nested nodes.
            else:
                p.moveToThreadNext()
        return files
    #@+node:ekr.20190108054803.1: *6* at.readFileAtPosition
    def readFileAtPosition(self, force, p):
        '''Read the @<file> node at p.'''
        at, c, fileName = self, self.c, p.anyAtFileNodeName()
        if p.isAtThinFileNode() or p.isAtFileNode():
            at.read(p, force=force)
        elif p.isAtAutoNode():
            at.readOneAtAutoNode(fileName, p)
        elif p.isAtEditNode():
            at.readOneAtEditNode(fileName, p)
        elif p.isAtShadowFileNode():
            at.readOneAtShadowNode(fileName, p)
        elif p.isAtAsisFileNode() or p.isAtNoSentFileNode():
            at.rememberReadPath(g.fullPath(c, p), p)
        elif p.isAtCleanNode():
            at.readOneAtCleanNode(p)
    #@+node:ekr.20080801071227.7: *5* at.readAtShadowNodes
    def readAtShadowNodes(self, p):
        '''Read all @shadow nodes in the p's tree.'''
        at = self
        after = p.nodeAfterTree()
        p = p.copy() # Don't change p in the caller.
        while p and p != after: # Don't use iterator.
            if p.isAtShadowFileNode():
                fileName = p.atShadowFileNodeName()
                at.readOneAtShadowNode(fileName, p)
                p.moveToNodeAfterTree()
            else:
                p.moveToThreadNext()
    #@+node:ekr.20070909100252: *5* at.readOneAtAutoNode
    def readOneAtAutoNode(self, fileName, p):
        '''Read an @auto file into p. Return the *new* position.'''
        at, c, ic = self, self.c, self.c.importCommands
        oldChanged = c.isChanged()
        at.default_directory = g.setDefaultDirectory(c, p, importing=True)
        fileName = c.os_path_finalize_join(at.default_directory, fileName)
        if not g.os_path_exists(fileName):
            g.error('not found: %r' % (p.h), nodeLink=p.get_UNL(with_proto=True))
            return p
        # Remember that we have seen the @auto node.
        # Fix bug 889175: Remember the full fileName.
        at.rememberReadPath(fileName, p)
        if not g.unitTesting:
            g.es("reading:", p.h)
        try:
            # For #451: return p.
            old_p = p.copy()
            at.scanAllDirectives(
                p,
                forcePythonSentinels=False,
                importing=True,
                reading=True,
            )
            p.v.b = '' # Required for @auto API checks.
            p.v._deleteAllChildren()
            p = ic.createOutline(fileName, parent=p.copy())
            # Do *not* select a postion here.
            # That would improperly expand nodes.
                # c.selectPosition(p)
        except Exception:
            p = old_p
            ic.errors += 1
            g.es_print('Unexpected exception importing', fileName)
            g.es_exception()
        if ic.errors:
            g.error('errors inhibited read @auto %s' % (fileName))
        elif c.persistenceController:
            c.persistenceController.update_after_read_foreign_file(p)
        # Finish.
        if ic.errors or not g.os_path_exists(fileName):
            p.clearDirty()
            c.setChanged(oldChanged)
        else:
            g.doHook('after-auto', c=c, p=p)
        return p
    #@+node:ekr.20090225080846.3: *5* at.readOneAtEditNode
    def readOneAtEditNode(self, fn, p):
        at = self
        c = at.c
        ic = c.importCommands
        at.default_directory = g.setDefaultDirectory(c, p, importing=True)
        fn = c.os_path_finalize_join(at.default_directory, fn)
        junk, ext = g.os_path_splitext(fn)
        # Fix bug 889175: Remember the full fileName.
        at.rememberReadPath(fn, p)
        if not g.unitTesting:
            g.es("reading: @edit %s" % (g.shortFileName(fn)))
        s, e = g.readFileIntoString(fn, kind='@edit')
        if s is None: return
        encoding = 'utf-8' if e is None else e
        # Delete all children.
        while p.hasChildren():
            p.firstChild().doDelete()
        changed = c.isChanged()
        head = ''
        ext = ext.lower()
        if ext in ('.html', '.htm'): head = '@language html\n'
        elif ext in ('.txt', '.text'): head = '@nocolor\n'
        else:
            language = ic.languageForExtension(ext)
            if language and language != 'unknown_language':
                head = '@language %s\n' % language
            else:
                head = '@nocolor\n'
        p.b = g.u(head) + g.toUnicode(s, encoding=encoding, reportErrors='True')
        if not changed: c.setChanged(False)
        g.doHook('after-edit', p=p)
    #@+node:ekr.20150204165040.5: *5* at.readOneAtCleanNode & helpers
    def readOneAtCleanNode(self, root):
        '''Update the @clean/@nosent node at root.'''
        at, c, x = self, self.c, self.c.shadowController
        fileName = g.fullPath(c, root)
        if not g.os_path_exists(fileName):
            g.es_print('not found: %s' % (fileName), color='red',
                nodeLink=root.get_UNL(with_proto=True))
            return
        at.rememberReadPath(fileName, root)
        at.initReadIvars(root, fileName)
            # Must be called before at.scanAllDirectives.
        at.scanAllDirectives(root)
            # Sets at.startSentinelComment/endSentinelComment.
        new_public_lines = at.read_at_clean_lines(fileName)
        old_private_lines = self.write_at_clean_sentinels(root)
        marker = x.markerFromFileLines(old_private_lines, fileName)
        old_public_lines, junk = x.separate_sentinels(old_private_lines, marker)
        if old_public_lines:
            new_private_lines = x.propagate_changed_lines(
                new_public_lines, old_private_lines, marker, p=root)
        else:
            new_private_lines = []
            root.b = ''.join(new_public_lines)
            return True
        if new_private_lines == old_private_lines:
            return True
        if not g.unitTesting:
            g.es("updating:", root.h)
        root.clearVisitedInTree()
        gnx2vnode = at.fileCommands.gnxDict
        contents = ''.join(new_private_lines)
        FastAtRead(c, gnx2vnode).read_into_root(contents, fileName, root)
        return True # Errors not detected.
    #@+node:ekr.20150204165040.7: *6* at.dump_lines
    def dump(self, lines, tag):
        '''Dump all lines.'''
        print('***** %s lines...\n' % tag)
        for s in lines:
            print(s.rstrip())
    #@+node:ekr.20150204165040.8: *6* at.read_at_clean_lines
    def read_at_clean_lines(self, fn):
        '''Return all lines of the @clean/@nosent file at fn.'''
        at = self
        s = at.openFileHelper(fn)
            # Use the standard helper. Better error reporting.
            # Important: uses 'rb' to open the file.
        s = g.toUnicode(s, encoding=at.encoding)
        s = s.replace('\r\n', '\n')
            # Suppress meaningless "node changed" messages.
        return g.splitLines(s)
    #@+node:ekr.20150204165040.9: *6* at.write_at_clean_sentinels (changed)
    def write_at_clean_sentinels(self, root):
        '''
        Return all lines of the @clean tree as if it were
        written as an @file node.
        '''
        at = self.c.atFileCommands
        at.getFile(root, kind='@nosent', sentinels=True)
        s = g.toUnicode(at.stringOutput, encoding=at.encoding)
        return g.splitLines(s)
    #@+node:ekr.20080711093251.7: *5* at.readOneAtShadowNode & helper
    def readOneAtShadowNode(self, fn, p, force=False):

        at = self; c = at.c; x = c.shadowController
        if not fn == p.atShadowFileNodeName():
            return at.error('can not happen: fn: %s != atShadowNodeName: %s' % (
                fn, p.atShadowFileNodeName()))
        # Fix bug 889175: Remember the full fileName.
        at.rememberReadPath(fn, p)
        at.default_directory = g.setDefaultDirectory(c, p, importing=True)
        fn = c.os_path_finalize_join(at.default_directory, fn)
        shadow_fn = x.shadowPathName(fn)
        shadow_exists = g.os_path_exists(shadow_fn) and g.os_path_isfile(shadow_fn)
        # Delete all children.
        while p.hasChildren():
            p.firstChild().doDelete()
        if shadow_exists:
            at.read(p, atShadow=True, force=force)
        else:
            if not g.unitTesting: g.es("reading:", p.h)
            ok = at.importAtShadowNode(fn, p)
            if ok:
                # Create the private file automatically.
                at.writeOneAtShadowNode(p, force=True)
    #@+node:ekr.20080712080505.1: *6* at.importAtShadowNode
    def importAtShadowNode(self, fn, p):
        at = self; c = at.c; ic = c.importCommands
        oldChanged = c.isChanged()
        # Delete all the child nodes.
        while p.hasChildren():
            p.firstChild().doDelete()
        # Import the outline, exactly as @auto does.
        ic.createOutline(fn, parent=p.copy(), atShadow=True)
        if ic.errors:
            g.error('errors inhibited read @shadow', fn)
        if ic.errors or not g.os_path_exists(fn):
            p.clearDirty()
            c.setChanged(oldChanged)
        # else: g.doHook('after-shadow', p = p)
        return ic.errors == 0
    #@+node:ekr.20180622110112.1: *4* at.fast_read_into_root
    def fast_read_into_root(self, c, contents, gnx2vnode, path, root):
        '''A convenience wrapper for FastAtReAD.read_into_root()'''
        return FastAtRead(c, gnx2vnode).read_into_root(contents, path, root)
    #@+node:ekr.20041005105605.116: *4* at.Reading utils...
    #@+node:ekr.20041005105605.119: *5* at.createImportedNode
    def createImportedNode(self, root, headline):
        at = self
        if at.importRootSeen:
            p = root.insertAsLastChild()
            p.initHeadString(headline)
        else:
            # Put the text into the already-existing root node.
            p = root
            at.importRootSeen = True
        p.v.setVisited() # Suppress warning about unvisited node.
        return p
    #@+node:ekr.20130911110233.11286: *5* at.initReadLine
    def initReadLine(self, s):
        '''Init the ivars so that at.readLine will read all of s.'''
        at = self
        at.read_i = 0
        at.read_lines = g.splitLines(s)
        at._file_bytes = g.toEncodedString(s)
    #@+node:ekr.20041005105605.120: *5* at.parseLeoSentinel
    def parseLeoSentinel(self, s):
        '''
        Parse the sentinel line s.
        If the sentinel is valid, set at.encoding, at.readVersion, at.readVersion5.
        '''
        at, c = self, self.c
        # Set defaults.
        encoding = c.config.default_derived_file_encoding
        readVersion, readVersion5 = None, None
        new_df, start, end, isThin = False, '', '', False
        # Example: \*@+leo-ver=5-thin-encoding=utf-8,.*/
        pattern = re.compile(r'(.+)@\+leo(-ver=([0123456789]+))?(-thin)?(-encoding=(.*)(\.))?(.*)')
            # The old code weirdly allowed '.' in version numbers.
            # group 1: opening delim
            # group 2: -ver=
            # group 3: version number
            # group(4): -thin
            # group(5): -encoding=utf-8,.
            # group(6): utf-8,
            # group(7): .
            # group(8): closing delim.
        m = pattern.match(s)
        valid = bool(m)
        if valid:
            start = m.group(1) # start delim
            valid = bool(start)
        if valid:
            new_df = bool(m.group(2)) # -ver=
            if new_df:
                # Set the version number.
                if m.group(3):
                    readVersion = m.group(3)
                    readVersion5 = readVersion >= '5'
                else:
                    valid = False
        if valid:
            # set isThin
            isThin = bool(m.group(4))
        if valid and m.group(5):
            # set encoding.
            encoding = m.group(6)
            if encoding and encoding.endswith(','):
                # Leo 4.2 or after.
                encoding = encoding[:-1]
            if not g.isValidEncoding(encoding):
                g.es_print("bad encoding in derived file:", encoding)
                valid = False
        if valid:
            end = m.group(8) # closing delim
        if valid:
            at.encoding = encoding
            at.readVersion = readVersion
            at.readVersion5 = readVersion5
        return valid, new_df, start, end, isThin
    #@+node:ekr.20130911110233.11284: *5* at.readFileToUnicode & helpers
    def readFileToUnicode(self, fn):
        '''
        Carefully sets at.encoding, then uses at.encoding to convert the file
        to a unicode string.

        Sets at.encoding as follows:
        1. Use the BOM, if present. This unambiguously determines the encoding.
        2. Use the -encoding= field in the @+leo header, if present and valid.
        3. Otherwise, uses existing value of at.encoding, which comes from:
            A. An @encoding directive, found by at.scanAllDirectives.
            B. The value of c.config.default_derived_file_encoding.

        Returns the string, or None on failure.

        This method is now part of the main @file read code.
        at.openFileForReading calls this method to read all @file nodes.
        Previously only at.scanHeaderForThin (import code) called this method.
        '''
        at = self
        s = at.openFileHelper(fn)
        if s is not None:
            e, s = g.stripBOM(s)
            if e:
                # The BOM determines the encoding unambiguously.
                s = g.toUnicode(s, encoding=e)
            else:
                # Get the encoding from the header, or the default encoding.
                s_temp = g.toUnicode(s, 'ascii', reportErrors=False)
                e = at.getEncodingFromHeader(fn, s_temp)
                s = g.toUnicode(s, encoding=e)
            s = s.replace('\r\n', '\n')
            at.encoding = e
            at.initReadLine(s)
        return s
    #@+node:ekr.20130911110233.11285: *6* at.openFileHelper
    def openFileHelper(self, fn):
        '''Open a file, reporting all exceptions.'''
        at = self
        s = None
        try:
            f = open(fn, 'rb')
            s = f.read()
            f.close()
        except IOError:
            at.error('can not open %s' % (fn))
        except Exception:
            at.error('Exception reading %s' % (fn))
            g.es_exception()
        return s
    #@+node:ekr.20130911110233.11287: *6* at.getEncodingFromHeader
    def getEncodingFromHeader(self, fn, s):
        '''
        Return the encoding given in the @+leo sentinel, if the sentinel is
        present, or the previous value of at.encoding otherwise.
        '''
        at = self
        if at.errors:
            g.trace('can not happen: at.errors > 0')
            e = at.encoding
            if g.unitTesting: assert False, g.callers()
                # This can happen when the showTree command in a unit test is left on.
                # A @file/@clean node is created which refers to a non-existent file.
                # It's surprisingly difficult to set at.error=0 safely elsewhere.
                # Otoh, I'm not sure why this test here is ever really useful.
        else:
            at.initReadLine(s)
            old_encoding = at.encoding
            assert old_encoding
            at.encoding = None
            # Execute scanHeader merely to set at.encoding.
            at.scanHeader(fn, giveErrors=False)
            e = at.encoding or old_encoding
        assert e
        return e
    #@+node:ekr.20041005105605.128: *5* at.readLine
    def readLine(self):
        """
        Read one line from file using the present encoding.
        Returns at.read_lines[at.read_i++]
        """
        # This is an old interface, now used only by at.scanHeader.
        # For now, it's not worth replacing.
        at = self
        if at.read_i < len(at.read_lines):
            s = at.read_lines[at.read_i]
            at.read_i += 1
            return s
        else:
            return '' # Not an error.
    #@+node:ekr.20041005105605.129: *5* at.scanHeader
    def scanHeader(self, fileName, giveErrors=True):
        """
        Scan the @+leo sentinel, using the old readLine interface.

        Sets self.encoding, and self.start/endSentinelComment.

        Returns (firstLines,new_df,isThinDerivedFile) where:
        firstLines        contains all @first lines,
        new_df            is True if we are reading a new-format derived file.
        isThinDerivedFile is True if the file is an @thin file.
        """
        at = self
        new_df, isThinDerivedFile = False, False
        firstLines = [] # The lines before @+leo.
        s = self.scanFirstLines(firstLines)
        valid = len(s) > 0
        if valid:
            valid, new_df, start, end, isThinDerivedFile = at.parseLeoSentinel(s)
        if valid:
            at.startSentinelComment = start
            at.endSentinelComment = end
        elif giveErrors:
            at.error("No @+leo sentinel in: %s" % fileName)
            g.trace(g.callers())
        return firstLines, new_df, isThinDerivedFile
    #@+node:ekr.20041005105605.130: *6* at.scanFirstLines
    def scanFirstLines(self, firstLines):
        '''
        Append all lines before the @+leo line to firstLines.

        Empty lines are ignored because empty @first directives are
        ignored.

        We can not call sentinelKind here because that depends on the comment
        delimiters we set here.
        '''
        at = self
        s = at.readLine()
        while s and s.find("@+leo") == -1:
            firstLines.append(s)
            s = at.readLine()
        return s
    #@+node:ekr.20050103163224: *5* at.scanHeaderForThin (import code)
    def scanHeaderForThin(self, fileName):
        '''
        Return true if the derived file is a thin file.

        This is a kludgy method used only by the import code.'''
        at = self
        at.readFileToUnicode(fileName)
            # inits at.readLine.
        junk, junk, isThin = at.scanHeader(None)
            # scanHeader uses at.readline instead of its args.
            # scanHeader also sets at.encoding.
        return isThin
    #@+node:ekr.20041005105605.132: *3* at.Writing
    #@+node:ekr.20041005105605.133: *4* Writing (top level)
    #@+node:ekr.20041005105605.154: *5* at.asisWrite & helper
    def asisWrite(self, root, toString=False):
        at = self; c = at.c
        c.endEditing() # Capture the current headline.
        c.init_error_dialogs()
        try:
            # Note: @asis always writes all nodes,
            # so there can be no orphan or ignored nodes.
            targetFileName = root.atAsisFileNodeName()
            at.initWriteIvars(root, targetFileName, toString=toString)
            # "look ahead" computation of eventual fileName.
            eventualFileName = c.os_path_finalize_join(
                at.default_directory, at.targetFileName)
            if at.shouldPromptForDangerousWrite(eventualFileName, root):
                # Prompt if writing a new @asis node would overwrite the existing file.
                ok = self.promptForDangerousWrite(eventualFileName, kind='@asis')
                if ok:
                    # Fix bug 889175: Remember the full fileName.
                    at.rememberReadPath(eventualFileName, root)
                else:
                    g.es("not written:", eventualFileName)
                    return
            if at.errors:
                return
            if not at.openFileForWriting(root, targetFileName, toString):
                # Calls at.addAtIgnore() if there are errors.
                return
            for p in root.self_and_subtree(copy=False):
                at.writeAsisNode(p)
            at.closeWriteFile()
            at.replaceTargetFileIfDifferent(root) # Sets/clears dirty and orphan bits.
        except Exception:
            at.writeException(root) # Sets dirty and orphan bits.

    silentWrite = asisWrite # Compatibility with old scripts.
    #@+node:ekr.20170331141933.1: *6* at.writeAsisNode
    def writeAsisNode(self, p):
        '''Write the p's node to an @asis file.'''
        at = self
        # Write the headline only if it starts with '@@'.
        s = p.h
        if g.match(s, 0, "@@"):
            s = s[2:]
            if s:
                at.outputFile.write(s)
        # Write the body.
        s = p.b
        if s:
            s = g.toEncodedString(s, at.encoding, reportErrors=True)
            at.outputStringWithLineEndings(s)

    #@+node:ekr.20190109160056.1: *5* at.getAsIs (new)
    def getAsIs(self, root):
        '''Write the @asis node to a string.'''
        at = self; c = at.c
        c.endEditing() # Capture the current headline.
        c.init_error_dialogs()
        try:
            # Note: @asis always writes all nodes,
            # so there can be no orphan or ignored nodes.
            at.targetFileName = "<string-file>"
            at.initWriteIvars(root, at.targetFileName, toString=True)
            at.openStringForWriting(root)
                # Sets at.outputFile, etc.
            for p in root.self_and_subtree(copy=False):
                at.writeAsisNode(p)
            at.closeWriteFile()
            at.fileChangedFlag = False
        except Exception:
            at.writeException(root) # Sets dirty and orphan bits.
        return at.stringOutput
    #@+node:ekr.20190109160056.2: *5* at.getAtAuto (new)
    def getAtAuto(self, root, trialWrite=False):
            # Set only by Importer.trial_write.
            # Suppresses call to update_before_write_foreign_file below.
        '''
        Write the root @auto node to a string, and return it.
        File indices *must* have already been assigned.
        '''
        at, c = self, self.c
        c.endEditing() # Capture the current headline.
        #
        # Init
        fileName = root.atAutoNodeName()
        at.targetFileName = "<string-file>"
        at.initWriteIvars(root, at.targetFileName,
            nosentinels=True, toString=True)
        at.openStringForWriting(root)
            # Sets at.outputFile, etc.
        #
        # Dispatch the proper writer.
        junk, ext = g.os_path_splitext(fileName)
        writer = at.dispatch(ext, root)
        if writer:
            writer(root)
        elif root.isAtAutoRstNode():
            # An escape hatch: fall back to the theRst writer
            # if there is no rst writer plugin.
            ok2 = c.rstCommands.writeAtAutoFile(root, fileName, at.outputFile)
            if not ok2: at.errors += 1
        else:
            # leo 5.6: allow undefined section references in all @auto files.
            ivar = 'allow_undefined_refs'
            try:
                setattr(at, ivar, True)
                at.writeOpenFile(root, nosentinels=True, toString=True)
            finally:
                if hasattr(at, ivar):
                    delattr(at, ivar)
        at.closeWriteFile()
            # Sets stringOutput if toString is True.
        ###
            # if at.errors:
                # isAtAutoRst = root.isAtAutoRstNode()
                # at.replaceTargetFileIfDifferent(root, ignoreBlankLines=isAtAutoRst)
                    # # Sets/clears dirty and orphan bits.
            # else:
                # g.es("not written:", fileName)
                # ### at.addAtIgnore(root)
        return at.stringOutput if at.errors == 0 else ''
    #@+node:ekr.20190109160056.3: *5* at.getAtEdit (new)
     ### at.writeOneAtEditNode(child1, toString=True)
    def getAtEdit(self, root):
        '''Write one @edit node.'''
        at, c = self, self.c
        c.endEditing()
        ### c.init_error_dialogs()
        if root.hasChildren():
            g.error('@edit nodes must not have children')
            g.es('To save your work, convert @edit to @auto, @file or @clean')
            return False
        ### at.default_directory = g.setDefaultDirectory(c, p, importing=True)
        at.targetFileName = root.atEditNodeName()
        at.initWriteIvars(root, at.targetFileName,
            atEdit=True, nosentinels=True, toString=True)
        # Compute the file's contents.
        # Unlike the @clean/@nosent file logic, it does not add a final newline.
        contents = ''.join([s for s in g.splitLines(root.b)
            if at.directiveKind4(s, 0) == at.noDirective])
        ### at.stringOutput = contents
        return contents
    #@+node:ekr.20190109142026.1: *5* at.getFile (new)
    def getFile(self, root, kind, sentinels=True):
        """Write a 4.x derived file to a string, and return it.
        root is the position of an @<file> node.
        """
        assert kind in ('@clean', '@file', '@nosent', '@shadow', '@thin', '@test'), repr(kind)
        at, c = self, self.c
        c.endEditing() # Capture the current headline.
        at.targetFileName = "<string-file>"
        at.initWriteIvars(root, at.targetFileName,
            nosentinels=not sentinels, toString=True)
        at.openStringForWriting(root)
            # Sets at.outputFile, etc.
        try:
            at.writeOpenFile(root, nosentinels=not sentinels, toString=True)
            assert root == at.root, 'write'
            at.closeWriteFile()
            at.fileChangedFlag = False
            # Major bug: failure to clear this wipes out headlines!
            # Minor bug: sometimes this causes slight problems...
            if hasattr(self.root.v, 'tnodeList'):
                delattr(self.root.v, 'tnodeList')
                root.v._p_changed = True
        except Exception:
            if hasattr(self.root.v, 'tnodeList'):
                delattr(self.root.v, 'tnodeList')
            at.exception("exception preprocessing script")
            root.v._p_changed = True
        return g.toUnicode(at.stringOutput)
    #@+node:ekr.20041005105605.142: *5* at.openFileForWriting & helper
    def openFileForWriting(self, root, fileName, toString):
        at = self
        at.outputFile = None
        if toString:
            at.shortFileName = g.shortFileName(fileName)
            at.outputFileName = "<string: %s>" % at.shortFileName
            at.outputFile = g.FileLikeObject()
        else:
            ok = at.openFileForWritingHelper(fileName)
            if not ok:
                at.outputFile = None
                at.addAtIgnore(root)
        return at.outputFile is not None
    #@+node:ekr.20041005105605.143: *6* at.openFileForWritingHelper & helper
    def openFileForWritingHelper(self, fileName):
        '''Open the file and return True if all went well.'''
        at = self; c = at.c
        try:
            at.shortFileName = g.shortFileName(fileName)
            at.targetFileName = c.os_path_finalize_join(
                at.default_directory, fileName)
            path = g.os_path_dirname(at.targetFileName)
            if not path or not g.os_path_exists(path):
                if path:
                    path = g.makeAllNonExistentDirectories(path, c=c)
                if not path or not g.os_path_exists(path):
                    path = g.os_path_dirname(at.targetFileName)
                    at.writeError("path does not exist: " + path)
                    return False
        except Exception:
            at.exception("exception creating path: %s" % repr(path))
            g.es_exception()
            return False
        if g.os_path_exists(at.targetFileName):
            try:
                if not os.access(at.targetFileName, os.W_OK):
                    at.writeError("can not open: read only: " + at.targetFileName)
                    return False
            except AttributeError:
                pass # os.access() may not exist on all platforms.
        try:
            old_output_fn = at.outputFileName
                # Fix bug: https://bugs.launchpad.net/leo-editor/+bug/1260547
            at.outputFileName = None
            kind, at.outputFile = self.openForWrite(at.outputFileName, 'wb')
            if not at.outputFile:
                kind = 'did not overwrite' if kind == 'check' else 'can not create'
                at.writeError("%s %s" % (kind, old_output_fn))
                return False
        except Exception:
            at.exception("exception creating:" + old_output_fn)
            return False
        return True
    #@+node:bwmulder.20050101094804: *7* at.openForWrite
    def openForWrite(self, filename, wb='wb'):
        '''Open a file for writes, handling shadow files.'''
        at = self; c = at.c; x = c.shadowController
        try:
            # 2011/10/11: in "quick edit/save" mode the .leo file may not have a name.
            if c.fileName():
                shadow_filename = x.shadowPathName(filename)
                self.writing_to_shadow_directory = os.path.exists(shadow_filename)
                open_file_name = shadow_filename if self.writing_to_shadow_directory else filename
                self.shadow_filename = shadow_filename if self.writing_to_shadow_directory else None
            else:
                self.writing_to_shadow_directory = False
                open_file_name = filename
            if self.writing_to_shadow_directory:
                x.message('writing %s' % shadow_filename)
                f = g.FileLikeObject()
                return 'shadow', f
            else:
                ok = c.checkFileTimeStamp(at.targetFileName)
                if ok:
                    f = g.FileLikeObject()
                else:
                    f = None
                # return 'check',ok and open(open_file_name,wb)
                return 'check', f
        except IOError:
            if not g.app.unitTesting:
                g.error('openForWrite: exception opening file: %s' % (open_file_name))
                g.es_exception()
            return 'error', None
    #@+node:ekr.20190109145850.1: *5* at.openStringForWriting (new)
    def openStringForWriting(self, root):
        at = self
        fn = root.anyAtFileNodeName() or root.h # use root.h for unit tests.
        assert fn, repr(root)
        at.shortFileName = g.shortFileName(fn)
        at.outputFileName = "<string: %s>" % at.shortFileName
        at.outputFile = g.FileLikeObject()
        return True
    #@+node:ekr.20041005105605.144: *5* at.write & helper (changed)
    def write(self, root, kind, nosentinels=False):
        """Write a 4.x derived file.
        root is the position of an @<file> node.
        """
        assert kind in ('@clean', '@file', '@nosent', '@shadow', '@thin', '@test'), repr(kind)
        at, c = self, self.c
        c.endEditing() # Capture the current headline.
        at.targetFileName = root.anyAtFileNodeName()
        at.initWriteIvars(
            root,
            at.targetFileName,
            nosentinels=nosentinels,
            toString=False,
        )
        # "look ahead" computation of eventual fileName.
        eventualFileName = c.os_path_finalize_join(
            at.default_directory, at.targetFileName)
       
        if at.shouldPromptForDangerousWrite(eventualFileName, root):
            # Prompt if writing a new @file or @clean node would
            # overwrite an existing file.
            ok = self.promptForDangerousWrite(eventualFileName, kind)
            if ok:
                at.rememberReadPath(eventualFileName, root)
            else:
                g.es("not written:", eventualFileName)
                # Fix #1031: do not add @ignore here!
                # @ignore will be added below if the write actually fails.
                return
        if not at.openFileForWriting(root, at.targetFileName, toString=False):
            # Calls at.addAtIgnore() if there are errors.
            return
        try:
            at.writeOpenFile(root, nosentinels=nosentinels, toString=False)
            assert root == at.root, 'write'
            at.closeWriteFile()
            if at.errors > 0:
                g.es("not written:", g.shortFileName(at.targetFileName))
                at.addAtIgnore(root)
            else:
                # Fix bug 889175: Remember the full fileName.
                at.rememberReadPath(eventualFileName, root)
                at.replaceTargetFileIfDifferent(root)
                    # Sets/clears dirty and orphan bits.
        except Exception:
            if hasattr(self.root.v, 'tnodeList'):
                delattr(self.root.v, 'tnodeList')
            at.writeException() # Sets dirty and orphan bits.
    #@+node:ekr.20041005105605.147: *5* at.writeAll & helpers
    def writeAll(self,
        writeAtFileNodesFlag=False,
        writeDirtyAtFileNodesFlag=False,
    ):
        """Write @file nodes in all or part of the outline"""
        at, c = self, self.c
        at.sameFiles = 0
        force = writeAtFileNodesFlag
        # This is the *only* place where these are set.
        # promptForDangerousWrite sets cancelFlag only if canCancelFlag is True.
        at.canCancelFlag = True
        at.cancelFlag = False
        at.yesToAll = False
        files, root = at.findFilesToWrite(force)
        for p in files:
            try:
                at.writeAllHelper(p, root, force)
            except Exception:
                at.internalWriteError(p)
        # Make *sure* these flags are cleared for other commands.
        at.canCancelFlag = False
        at.cancelFlag = False
        at.yesToAll = False
        # Say the command is finished.
        at.reportEndOfWrite(files, force, writeDirtyAtFileNodesFlag)
        if c.isChanged():
            # Save the outline if only persistence data nodes are dirty.
            at.saveOutlineIfPossible()
    #@+node:ekr.20190108052043.1: *6* at.findFilesToWrite
    def findFilesToWrite(self, force):
        '''
        Return a list of files to write.
        We must do this in a prepass, so as to avoid errors later.
        '''
        c = self.c
        if force:
            # The Write @<file> Nodes command.
            # Write all nodes in the selected tree.
            root = c.p
            p = c.p
            after = p.nodeAfterTree()
        else:
            # Write dirty nodes in the entire outline.
            root = c.rootPosition()
            p = c.rootPosition()
            after = None
        seen = set()
        files = []
        while p and p != after:
            if p.isAtIgnoreNode() and not p.isAtAsisFileNode():
                if p.isAnyAtFileNode():
                    c.ignored_at_file_nodes.append(p.h)
                # Note: @ignore not honored in @asis nodes.
                p.moveToNodeAfterTree() # 2011/10/08: Honor @ignore!
            elif p.isAnyAtFileNode():
                data = p.v, g.fullPath(c, p)
                if data not in seen:
                    seen.add(data)
                    files.append(p.copy())
                p.moveToThreadNext()
                    #525: Scan for nested @<file> nodes
            else:
                p.moveToThreadNext()
        if not force:
            files = [z for z in files if z.isDirty()]
        return files, root
        
    #@+node:ekr.20190108053115.1: *6* at.internalWriteError
    def internalWriteError(self, p):
        '''
        Fix bug 1260415: https://bugs.launchpad.net/leo-editor/+bug/1260415
        Give a more urgent, more specific, more helpful message.
        '''
        g.es_exception()
        g.es('Internal error writing: %s' % (p.h), color='red')
        g.es('Please report this error to:', color='blue')
        g.es('https://groups.google.com/forum/#!forum/leo-editor', color='blue')
        g.es('Warning: changes to this file will be lost', color='red')
        g.es('unless you can save the file successfully.', color='red')
    #@+node:ekr.20190108112519.1: *6* at.reportEndOfWrite
    def reportEndOfWrite(self, files, force, writeDirtyAtFileNodesFlag):
        
        at, c = self, self.c
        if g.unitTesting:
            return
        if not force and not writeDirtyAtFileNodesFlag:
            return
        if files:
            report = c.config.getBool('report-unchanged-files', default=True)
            if report:
                g.es("finished")
            elif at.sameFiles:
                g.es('finished. %s unchanged files' % at.sameFiles)
        elif force:
            g.warning("no @<file> nodes in the selected tree")
            # g.es("to write an unchanged @auto node,\nselect it directly.")
        else:
            g.es("no dirty @<file> nodes")
    #@+node:ekr.20140727075002.18108: *6* at.saveOutlineIfPossible
    def saveOutlineIfPossible(self):
        '''Save the outline if only persistence data nodes are dirty.'''
        c = self.c
        changed_positions = [p for p in c.all_unique_positions() if p.v.isDirty()]
        at_persistence = c.persistenceController and c.persistenceController.has_at_persistence_node()
        if at_persistence:
            changed_positions = [p for p in changed_positions
                if not at_persistence.isAncestorOf(p)]
        if not changed_positions:
            # g.warning('auto-saving @persistence tree.')
            c.setChanged(False)
            c.redraw()
    #@+node:ekr.20041005105605.149: *6* at.writeAllHelper & helper (changed)
    def writeAllHelper(self, p, root, force):
        '''
        Write one file for the at.writeAll.
        Do *not* write @auto files unless p == root.
        This prevents the write-all command from needlessly updating
        the @persistence data, thereby annoyingly changing the .leo file.
        '''
        ### Called only by at.writeAll.
        at = self
        at.root = root
        if not force and p.isDirty():
            at.autoBeautify(p)
        try:
            pathChanged = at.writePathChanged(p)
        except IOError:
            return
        # Tricky: @ignore not recognised in @asis nodes.
        if p.isAtAsisFileNode():
            at.asisWrite(p)
        elif p.isAtIgnoreNode():
            return # Handled in caller.
        elif p.isAtAutoNode():
            at.writeOneAtAutoNode(p, force=force) 
            # Do *not* clear the dirty bits the entries in @persistence tree here!
        elif p.isAtCleanNode():
            at.write(p, kind='@clean', nosentinels=True)
        elif p.isAtEditNode():
            at.writeOneAtEditNode(p)
        elif p.isAtNoSentFileNode():
            at.write(p, kind='@nosent', nosentinels=True)
        elif p.isAtShadowFileNode():
            at.writeOneAtShadowNode(p, force=force or pathChanged)
        elif p.isAtThinFileNode():
            at.write(p, kind='@thin')
        elif p.isAtFileNode():
            at.write(p, kind='@file')
        #
        # Clear the dirty bits in all descendant nodes.
        # The persistence data may still have to be written.
        for p2 in p.self_and_subtree(copy=False):
            p2.v.clearDirty()
    #@+node:ekr.20150602204757.1: *7* at.autoBeautify
    def autoBeautify(self, p):
        '''Auto beautify p's tree if allowed by settings and directives.'''
        c = self.c
        try:
            if not p.isDirty():
                return
            if leoBeautify.should_kill_beautify(p):
                return
            if c.config.getBool('tidy-autobeautify'):
                leoBeautify.beautifyPythonTree(event={'c': c, 'p0': p.copy()})
        except Exception:
            g.es('unexpected exception')
            g.es_exception()
    #@+node:ekr.20190108105509.1: *7* at.writePathChanged
    def writePathChanged(self, p):
        '''
        Return True if the path has changed and the user allows it.
        raise IOError if the user forbids the write.
        Return False if the path has not changed.
        '''
        at, c = self, self.c
        if p.isAtIgnoreNode() and not p.isAtAsisFileNode():
            return False
        oldPath = g.os_path_normcase(at.getPathUa(p))
        newPath = g.os_path_normcase(g.fullPath(c, p))
        pathChanged = oldPath and oldPath != newPath
        # 2010/01/27: suppress this message during save-as and save-to commands.
        if pathChanged and not c.ignoreChangedPaths:
            ok = at.promptForDangerousWrite(
                fileName=None,
                kind=None,
                message='%s\n%s' % (
                    g.tr('path changed for %s' % (p.h)),
                    g.tr('write this file anyway?')))
            if not ok:
                raise IOError
            at.setPathUa(p, newPath) # Remember that we have changed paths.
        return pathChanged
    #@+node:ekr.20070806105859: *5* at.writeAtAutoNodes & writeDirtyAtAutoNodes & helpers
    @cmd('write-at-auto-nodes')
    def writeAtAutoNodes(self, event=None):
        '''Write all @auto nodes in the selected outline.'''
        at = self; c = at.c
        c.init_error_dialogs()
        at.writeAtAutoNodesHelper(writeDirtyOnly=False)
        c.raise_error_dialogs(kind='write')

    @cmd('write-dirty-at-auto-nodes')
    def writeDirtyAtAutoNodes(self, event=None):
        '''Write all dirty @auto nodes in the selected outline.'''
        at = self; c = at.c
        c.init_error_dialogs()
        at.writeAtAutoNodesHelper(writeDirtyOnly=True)
        c.raise_error_dialogs(kind='write')
    #@+node:ekr.20070806141607: *6* at.writeOneAtAutoNode & helpers (changed)
    def writeOneAtAutoNode(self,
        p,
        force=False,
        ### toString=False,
        trialWrite=False,
            # Set only by Importer.trial_write.
            # Suppresses call to update_before_write_foreign_file below.
    ):
        '''
        Write p, an @auto node.
        File indices *must* have already been assigned.
        '''
        toString = False
        at, c = self, self.c
        root = p.copy()
        fileName = p.atAutoNodeName()
        if not fileName and not toString:
            return False
        at.default_directory = g.setDefaultDirectory(c, p, importing=True)
        fileName = c.os_path_finalize_join(at.default_directory, fileName)
        if not toString and at.shouldPromptForDangerousWrite(fileName, root):
            # Prompt if writing a new @auto node would overwrite the existing file.
            ok = self.promptForDangerousWrite(fileName, kind='@auto')
            if not ok:
                g.es("not written:", fileName)
                return False
        # Fix bug 889175: Remember the full fileName.
        at.rememberReadPath(fileName, root)
        # This code is similar to code in at.write.
        c.endEditing() # Capture the current headline.
        at.targetFileName = "<string-file>" if toString else fileName
        at.initWriteIvars(
            root,
            at.targetFileName,
            nosentinels=True,
            toString=toString,
        )
        if c.persistenceController and not trialWrite:
            c.persistenceController.update_before_write_foreign_file(root)
        ok = at.openFileForWriting(root, fileName=fileName, toString=toString)
            # Calls at.addAtIgnore() if there are errors.
        if not ok:
            if not toString:
                g.es("not written:", fileName)
                at.addAtIgnore(root)
            return False
        #
        # Dispatch the proper writer.
        junk, ext = g.os_path_splitext(fileName)
        writer = at.dispatch(ext, root)
        if writer:
            writer(root)
        elif root.isAtAutoRstNode():
            # An escape hatch: fall back to the theRst writer
            # if there is no rst writer plugin.
            ok2 = c.rstCommands.writeAtAutoFile(root, fileName, at.outputFile)
            if not ok2: at.errors += 1
        else:
            # leo 5.6: allow undefined section references in all @auto files.
            ivar = 'allow_undefined_refs'
            try:
                setattr(at, ivar, True)
                at.writeOpenFile(root, nosentinels=True, toString=toString)
            finally:
                if hasattr(at, ivar):
                    delattr(at, ivar)
        at.closeWriteFile()
            # Sets stringOutput if toString is True.
        if at.errors == 0:
            isAtAutoRst = root.isAtAutoRstNode()
            at.replaceTargetFileIfDifferent(root, ignoreBlankLines=isAtAutoRst)
                # Sets/clears dirty and orphan bits.
        else:
            g.es("not written:", fileName)
            at.addAtIgnore(root)
        return at.errors == 0
    #@+node:ekr.20190109163934.24: *7* at.writeAtAutoNodesHelper
    def writeAtAutoNodesHelper(self, writeDirtyOnly=True): ### toString=False, 
        """Write @auto nodes in the selected outline"""
        at = self; c = at.c
        p = c.p; after = p.nodeAfterTree()
        found = False
        while p and p != after:
            if (
                p.isAtAutoNode() and not p.isAtIgnoreNode() and
                (p.isDirty() or not writeDirtyOnly)
            ):
                ok = at.writeOneAtAutoNode(p, force=True)
                if ok:
                    found = True
                    p.moveToNodeAfterTree()
                else:
                    p.moveToThreadNext()
            else:
                p.moveToThreadNext()
        if not g.unitTesting:
            if found:
                g.es("finished")
            elif writeDirtyOnly:
                g.es("no dirty @auto nodes in the selected tree")
            else:
                g.es("no @auto nodes in the selected tree")
    #@+node:ekr.20140728040812.17993: *7* at.dispatch & helpers
    def dispatch(self, ext, p):
        '''Return the correct writer function for p, an @auto node.'''
        at = self
        # Match @auto type before matching extension.
        return at.writer_for_at_auto(p) or at.writer_for_ext(ext)
    #@+node:ekr.20140728040812.17995: *8* at.writer_for_at_auto
    def writer_for_at_auto(self, root):
        '''A factory returning a writer function for the given kind of @auto directive.'''
        at = self
        d = g.app.atAutoWritersDict
        for key in d.keys():
            aClass = d.get(key)
            if aClass and g.match_word(root.h, 0, key):

                def writer_for_at_auto_cb(root):
                    # pylint: disable=cell-var-from-loop
                    try:
                        writer = aClass(at.c)
                        s = writer.write(root)
                        return s
                    except Exception:
                        g.es_exception()
                        return None

                return writer_for_at_auto_cb
        return None
    #@+node:ekr.20140728040812.17997: *8* at.writer_for_ext
    def writer_for_ext(self, ext):
        '''A factory returning a writer function for the given file extension.'''
        at = self
        d = g.app.writersDispatchDict
        aClass = d.get(ext)
        if aClass:

            def writer_for_ext_cb(root):
                try:
                    return aClass(at.c).write(root)
                except Exception:
                    g.es_exception()
                    return None

            return writer_for_ext_cb
        else:
            return None
    #@+node:ekr.20080711093251.3: *5* at.writeAtShadowNodes & writeDirtyAtShadowNodes & helpers
    @cmd('write-at-shadow-nodes')
    def writeAtShadowNodes(self, event=None):
        '''Write all @shadow nodes in the selected outline.'''
        at = self; c = at.c
        c.init_error_dialogs()
        val = at.writeAtShadowNodesHelper(writeDirtyOnly=False)
        c.raise_error_dialogs(kind='write')
        return val

    @cmd('write-dirty-at-shadow-nodes')
    def writeDirtyAtShadowNodes(self, event=None):
        '''Write all dirty @shadow nodes in the selected outline.'''
        at = self; c = at.c
        c.init_error_dialogs()
        val = at.writeAtShadowNodesHelper(writeDirtyOnly=True)
        c.raise_error_dialogs(kind='write')
        return val
    #@+node:ekr.20080711093251.5: *6* at.writeOneAtShadowNode & helpers
    def writeOneAtShadowNode(self, p, force=False, toString=False):
        '''
        Write p, an @shadow node.
        File indices *must* have already been assigned.
        '''
        at, c, x = self, self.c, self.c.shadowController
        root = p.copy()
        fn = p.atShadowFileNodeName()
        if not fn:
            g.error('can not happen: not an @shadow node', p.h)
            return False
        # A hack to support unknown extensions.
        self.adjustTargetLanguage(fn) # May set c.target_language.
        fn = g.fullPath(c, p)
        at.default_directory = g.os_path_dirname(fn)
        # Bug fix 2010/01/18: Make sure we can compute the shadow directory.
        private_fn = x.shadowPathName(fn)
        if not private_fn:
            return False
        if not toString and at.shouldPromptForDangerousWrite(fn, root):
            # Prompt if writing a new @shadow node would overwrite the existing public file.
            ok = self.promptForDangerousWrite(fn, kind='@shadow')
            if ok:
                # Fix bug 889175: Remember the full fileName.
                at.rememberReadPath(fn, root)
            else:
                g.es("not written:", fn)
                return
        c.endEditing() # Capture the current headline.
        at.initWriteIvars(
            root,
            targetFileName=None, # Not used.
            atShadow=True,
            nosentinels=None,
                # set below.  Affects only error messages (sometimes).
            toString=False,
                # True: create a FileLikeObject below.
            forcePythonSentinels=True,
                # A hack to suppress an error message.
                # The actual sentinels will be set below.
        )
        #
        # Bug fix: Leo 4.5.1:
        # use x.markerFromFileName to force the delim to match
        # what is used in x.propegate changes.
        marker = x.markerFromFileName(fn)
        at.startSentinelComment, at.endSentinelComment = marker.getDelims()
        if g.app.unitTesting:
            ivars_dict = g.getIvarsDict(at)
        # Write the public and private files to public_s and private_s strings.
        data = []
        for sentinels in (False, True):
            # Specify encoding explicitly.
            theFile = at.openStringFile(fn, encoding=at.encoding)
            at.sentinels = sentinels
            at.writeOpenFile(root,
                nosentinels=not sentinels, toString=False)
                    # nosentinels only affects error messages.
            s = at.closeStringFile(theFile)
            data.append(s)
        # Set these new ivars for unit tests.
        # data has exactly two elements.
        # pylint: disable=unbalanced-tuple-unpacking
        at.public_s, at.private_s = data
        if g.app.unitTesting:
            exceptions = ('public_s', 'private_s', 'sentinels', 'stringOutput', 'outputContents')
            assert g.checkUnchangedIvars(at, ivars_dict, exceptions), 'writeOneAtShadowNode'
        if at.errors == 0 and not toString:
            # Write the public and private files.
            x.makeShadowDirectory(fn)
                # makeShadowDirectory takes a *public* file name.
            at.replaceFileWithString(private_fn, at.private_s)
            at.replaceFileWithString(fn, at.public_s)
        self.checkPythonCode(root, s=at.private_s, targetFn=fn)
        if at.errors == 0:
            root.clearDirty()
        else:
            g.error("not written:", at.outputFileName)
            at.addAtIgnore(root)
        return at.errors == 0
    #@+node:ekr.20080819075811.13: *7* adjustTargetLanguage
    def adjustTargetLanguage(self, fn):
        """Use the language implied by fn's extension if
        there is a conflict between it and c.target_language."""
        at = self
        c = at.c
        junk, ext = g.os_path_splitext(fn)
        if ext:
            if ext.startswith('.'): ext = ext[1:]
            language = g.app.extension_dict.get(ext)
            if language:
                c.target_language = language
            else:
                # An unknown language.
                pass # Use the default language, **not** 'unknown_language'
    #@+node:ekr.20190109153627.13: *6* at.writeAtShadowNodesHelper
    def writeAtShadowNodesHelper(self, toString=False, writeDirtyOnly=True):
        """Write @shadow nodes in the selected outline"""
        at = self; c = at.c
        p = c.p; after = p.nodeAfterTree()
        found = False
        while p and p != after:
            if p.atShadowFileNodeName() and not p.isAtIgnoreNode() and (p.isDirty() or not writeDirtyOnly):
                ok = at.writeOneAtShadowNode(p, toString=toString, force=True)
                if ok:
                    found = True
                    g.blue('wrote %s' % p.atShadowFileNodeName())
                    p.moveToNodeAfterTree()
                else:
                    p.moveToThreadNext()
            else:
                p.moveToThreadNext()
        if not g.unitTesting:
            if found:
                g.es("finished")
            elif writeDirtyOnly:
                g.es("no dirty @shadow nodes in the selected tree")
            else:
                g.es("no @shadow nodes in the selected tree")
        return found
    #@+node:ekr.20050506084734: *5* at.writeFromString
    def writeFromString(self, root, s, forcePythonSentinels=True, useSentinels=True):
        """
        Write a 4.x derived file from a string.

        This is at.write specialized for scripting.
        """
        at = self; c = at.c
        c.endEditing()
            # Capture the current headline, but don't change the focus!
        at.initWriteIvars(root, "<string-file>",
            nosentinels=not useSentinels,
            toString=True,
            forcePythonSentinels=forcePythonSentinels,
        )
        try:
            ok = at.openFileForWriting(root, at.targetFileName, toString=True)
                # Calls at.addAtIgnore() if there are errors.
            if g.app.unitTesting:
                assert ok, 'writeFromString' # string writes never fail.
            # Simulate writing the entire file so error recovery works.
            at.writeOpenFile(root,
                nosentinels=not useSentinels,
                toString=True,
                fromString=s,
            )
            at.closeWriteFile()
            # Major bug: failure to clear this wipes out headlines!
            # Minor bug: sometimes this causes slight problems...
            if root:
                if hasattr(self.root.v, 'tnodeList'):
                    delattr(self.root.v, 'tnodeList')
                root.v._p_changed = True
        except Exception:
            at.exception("exception preprocessing script")
        return at.stringOutput
    #@+node:ekr.20041005105605.151: *5* at.writeMissing & helper
    def writeMissing(self, p, toString=False):
        at = self; c = at.c
        writtenFiles = False
        c.init_error_dialogs()
        p = p.copy()
        after = p.nodeAfterTree()
        while p and p != after: # Don't use iterator.
            if p.isAtAsisFileNode() or (p.isAnyAtFileNode() and not p.isAtIgnoreNode()):
                at.targetFileName = p.anyAtFileNodeName()
                if at.targetFileName:
                    at.targetFileName = c.os_path_finalize_join(
                        self.default_directory, at.targetFileName)
                    if not g.os_path_exists(at.targetFileName):
                        ok = at.openFileForWriting(p, at.targetFileName, toString)
                            # Calls at.addAtIgnore() if there are errors.
                        if ok:
                            at.writeMissingNode(p)
                            writtenFiles = True
                            at.closeWriteFile()
                p.moveToNodeAfterTree()
            elif p.isAtIgnoreNode():
                p.moveToNodeAfterTree()
            else:
                p.moveToThreadNext()
        if not g.unitTesting:
            if writtenFiles > 0:
                g.es("finished")
            else:
                g.es("no @file node in the selected tree")
        c.raise_error_dialogs(kind='write')
    #@+node:ekr.20041005105605.152: *6* at.writeMissingNode
    def writeMissingNode(self, p):

        at = self
        if p.isAtAsisFileNode():
            at.asisWrite(p)
        elif p.isAtNoSentFileNode():
            at.write(p, kind='@nosent', nosentinels=True)
        elif p.isAtFileNode():
            at.write(p, kind='@file')
        else:
            g.trace('can not happen: unknown @file node')
    #@+node:ekr.20090225080846.5: *5* at.writeOneAtEditNode
    def writeOneAtEditNode(self, p, toString=False, force=False):
        '''Write one @edit node.'''
        at = self; c = at.c
        root = p.copy()
        c.endEditing()
        c.init_error_dialogs()
        fn = p.atEditNodeName()
        if not fn and not toString:
            return False
        if p.hasChildren():
            g.error('@edit nodes must not have children')
            g.es('To save your work, convert @edit to @auto, @file or @clean')
            return False
        at.default_directory = g.setDefaultDirectory(c, p, importing=True)
        fn = c.os_path_finalize_join(at.default_directory, fn)
        if not force and at.shouldPromptForDangerousWrite(fn, root):
            # Prompt if writing a new @edit node would overwrite the existing file.
            ok = self.promptForDangerousWrite(fn, kind='@edit')
            if ok:
                # Fix bug 889175: Remember the full fileName.
                at.rememberReadPath(fn, root)
            else:
                g.es("not written:", fn)
                return False
        at.targetFileName = fn
        at.initWriteIvars(root, at.targetFileName,
            atEdit=True,
            nosentinels=True,
            toString=toString,
        )
        # Compute the file's contents.
        # Unlike the @clean/@nosent file logic, it does not add a final newline.
        contents = ''.join([s for s in g.splitLines(p.b)
            if at.directiveKind4(s, 0) == at.noDirective])
        if toString:
            at.stringOutput = contents
            return True
        ok = at.openFileForWriting(root, fileName=fn, toString=False)
            # Calls at.addAtIgnore() if there are errors.
        if ok:
            self.os(contents)
            at.closeWriteFile()
            if at.errors:
                g.es("not written:", at.targetFileName)
                at.addAtIgnore(root)
            else:
                at.replaceTargetFileIfDifferent(root)
                    # calls at.addAtIgnore if there are errors.
        c.raise_error_dialogs(kind='write')
        return ok
    #@+node:ekr.20041005105605.157: *5* at.writeOpenFile
    def writeOpenFile(self, root, nosentinels=False, toString=False, fromString=''):
        """Do all writes except asis writes."""
        at = self
        s = fromString if fromString else root.v.b
        root.clearAllVisitedInTree()
        at.putAtFirstLines(s)
        at.putOpenLeoSentinel("@+leo-ver=5")
        at.putInitialComment()
        at.putOpenNodeSentinel(root)
        at.putBody(root, fromString=fromString)
        at.putCloseNodeSentinel(root)
        # The -leo sentinel is required to handle @last.
        at.putSentinel("@-leo")
        root.setVisited()
        at.putAtLastLines(s)
        if not toString:
            at.warnAboutOrphandAndIgnoredNodes()
    #@+node:ekr.20041005105605.160: *4* Writing 4.x
    #@+node:ekr.20041005105605.161: *5* at.putBody & helpers
    def putBody(self, p, fromString=''):
        '''
        Generate the body enclosed in sentinel lines.
        Return True if the body contains an @others line.
        '''
        at = self
        ### if not at.sentinels: g.trace(at.sentinels, p.h, g.callers(4))
        # New in 4.3 b2: get s from fromString if possible.
        s = fromString if fromString else p.b
        p.v.setVisited()
            # Make sure v is never expanded again.
            # Suppress orphans check.
        s, trailingNewlineFlag = at.ensureTrailingNewline(s)
        at.raw = False # Bug fix.
        i = 0
        status = g.Bunch(
            at_comment_seen = False,
            at_delims_seen = False,
            at_warning_given = False,
            has_at_others = False,
            in_code = True,
        )
        while i < len(s):
            next_i = g.skip_line(s, i)
            assert next_i > i, 'putBody'
            kind = at.directiveKind4(s, i)
            at.putLine(i, kind, p, s, status)
            i = next_i
        # pylint: disable=no-member
            # g.bunch *does* have .in_code and has_at_others members.
        if not status.in_code:
            at.putEndDocLine()
        if not trailingNewlineFlag:
            if at.sentinels:
                pass # Never write @nonl
            elif not at.atEdit:
                at.onl()
        return status.has_at_others
    #@+node:ekr.20041005105605.162: *6* at.ensureTrailingNewline
    def ensureTrailingNewline(self, s):
        '''
        Ensure a trailing newline in s.
        If we add a trailing newline, we'll generate an @nonl sentinel below.

        - We always ensure a newline in @file and @thin trees.
        - This code is not used used in @asis trees.
        - New in Leo 4.4.3 b1: We add a newline in @clean/@nosent trees unless
          @bool force_newlines_in_at_nosent_bodies = False
        '''
        at = self
        if s:
            trailingNewlineFlag = s[-1] == '\n'
            if not trailingNewlineFlag:
                if at.sentinels or at.force_newlines_in_at_nosent_bodies:
                    s = s + '\n'
        else:
            trailingNewlineFlag = True # don't need to generate an @nonl
        return s, trailingNewlineFlag
    #@+node:ekr.20041005105605.163: *6* at.putLine
    def putLine(self, i, kind, p, s, status):
        '''Put the line at s[i:] of the given kind, updating the status.'''
        at = self
        if kind == at.noDirective:
            if status.in_code:
                if at.raw:
                    at.putCodeLine(s, i)
                else:
                    name, n1, n2 = at.findSectionName(s, i)
                    if name:
                        at.putRefLine(s, i, n1, n2, name, p)
                    else:
                        at.putCodeLine(s, i)
            else:
                at.putDocLine(s, i)
        elif at.raw:
            if kind == at.endRawDirective:
                at.raw = False
                at.putSentinel("@@end_raw")
            else:
                # Fix bug 784920: @raw mode does not ignore directives
                at.putCodeLine(s, i)
        elif kind in (at.docDirective, at.atDirective):
            assert not at.pending, 'putBody at.pending'
            if not status.in_code:
                # Bug fix 12/31/04: handle adjacent doc parts.
                at.putEndDocLine()
            at.putStartDocLine(s, i, kind)
            status.in_code = False
        elif kind in (at.cDirective, at.codeDirective):
            # Only @c and @code end a doc part.
            if not status.in_code:
                at.putEndDocLine()
            at.putDirective(s, i)
            status.in_code = True
        elif kind == at.allDirective:
            if status.in_code:
                if p == self.root:
                    at.putAtAllLine(s, i, p)
                else:
                    at.error('@all not valid in: %s' % (p.h))
            else: at.putDocLine(s, i)
        elif kind == at.othersDirective:
            if status.in_code:
                if status.has_at_others:
                    at.error('multiple @others in: %s' % (p.h))
                else:
                    at.putAtOthersLine(s, i, p)
                    status.has_at_others = True
            else:
                at.putDocLine(s, i)
        elif kind == at.rawDirective:
            at.raw = True
            at.putSentinel("@@raw")
        elif kind == at.endRawDirective:
            # Fix bug 784920: @raw mode does not ignore directives
            at.error('unmatched @end_raw directive: %s' % p.h)
        elif kind == at.startVerbatim:
            # Fix bug 778204: @verbatim not a valid Leo directive.
            if g.unitTesting:
                # A hack: unit tests for @shadow use @verbatim as a kind of directive.
                pass
            else:
                at.error('@verbatim is not a Leo directive: %s' % p.h)
        elif kind == at.miscDirective:
            # Fix bug 583878: Leo should warn about @comment/@delims clashes.
            if g.match_word(s, i, '@comment'):
                status.at_comment_seen = True
            elif g.match_word(s, i, '@delims'):
                status.at_delims_seen = True
            if (
                status.at_comment_seen and
                status.at_delims_seen and not
                status.at_warning_given
            ):
                status.at_warning_given = True
                at.error('@comment and @delims in node %s' % p.h)
            at.putDirective(s, i)
        else:
            at.error('putBody: can not happen: unknown directive kind: %s' % kind)
    #@+node:ekr.20041005105605.164: *5* writing code lines...
    #@+node:ekr.20041005105605.165: *6* at.@all
    #@+node:ekr.20041005105605.166: *7* at.putAtAllLine
    def putAtAllLine(self, s, i, p):
        """Put the expansion of @all."""
        at = self
        j, delta = g.skip_leading_ws_with_indent(s, i, at.tab_width)
        k = g.skip_to_end_of_line(s,i)
        at.putLeadInSentinel(s, i, j, delta)
        at.indent += delta
        at.putSentinel("@+" + s[j+1:k].strip())
            # s[j:k] starts with '@all'
        for child in p.children():
            at.putAtAllChild(child)
        at.putSentinel("@-all")
        at.indent -= delta
    #@+node:ekr.20041005105605.167: *7* at.putAtAllBody
    def putAtAllBody(self, p):
        """ Generate the body enclosed in sentinel lines."""
        at = self
        s = p.b
        p.v.setVisited()
            # Make sure v is never expanded again.
            # Suppress orphans check.
        if at.sentinels and s and s[-1] != '\n':
            s = s + '\n'
        i, inCode = 0, True
        while i < len(s):
            next_i = g.skip_line(s, i)
            assert(next_i > i)
            if inCode:
                # Use verbatim sentinels to write all directives.
                at.putCodeLine(s, i)
            else:
                at.putDocLine(s, i)
            i = next_i
        if not inCode:
            at.putEndDocLine()
    #@+node:ekr.20041005105605.169: *7* at.putAtAllChild
    def putAtAllChild(self, p):
        '''
        This code puts only the first of two or more cloned siblings, preceding
        the clone with an @clone n sentinel.
        
        This is a debatable choice: the cloned tree appears only once in the
        external file. This should be benign; the text created by @all is
        likely to be used only for recreating the outline in Leo. The
        representation in the derived file doesn't matter much.
        '''
        at = self
        at.putOpenNodeSentinel(p, inAtAll=True)
            # Suppress warnings about @file nodes.
        at.putAtAllBody(p)
        for child in p.children():
            at.putAtAllChild(child)
        at.putCloseNodeSentinel(p)
    #@+node:ekr.20041005105605.170: *6* at.@others (write)
    #@+node:ekr.20041005105605.173: *7* at.putAtOthersLine & helpers
    def putAtOthersLine(self, s, i, p):
        """Put the expansion of @others."""
        at = self
        j, delta = g.skip_leading_ws_with_indent(s, i, at.tab_width)
        k = g.skip_to_end_of_line(s,i)
        at.putLeadInSentinel(s, i, j, delta)
        at.indent += delta
        at.putSentinel("@+" + s[j+1:k].strip())
            # s[j:k] starts with '@others'
            # Never write lws in new sentinels.
        for child in p.children():
            p = child.copy()
            after = p.nodeAfterTree()
            while p and p != after:
                if at.validInAtOthers(p):
                    at.putOpenNodeSentinel(p)
                    at_others_flag = at.putBody(p)
                    at.putCloseNodeSentinel(p)
                    if at_others_flag:
                        p.moveToNodeAfterTree()
                    else:
                        p.moveToThreadNext()
                else:
                    p.moveToNodeAfterTree()
        # This is the same in both old and new sentinels.
        at.putSentinel("@-others")
        at.indent -= delta
    #@+node:ekr.20041005105605.172: *8* at.putAtOthersChild
    def putAtOthersChild(self, p):
        at = self
        at.putOpenNodeSentinel(p)
        at.putBody(p)
        at.putCloseNodeSentinel(p)
    #@+node:ekr.20041005105605.171: *8* at.validInAtOthers (write)
    def validInAtOthers(self, p):
        """
        Return True if p should be included in the expansion of the @others
        directive in the body text of p's parent.
        """
        at = self
        i = g.skip_ws(p.h, 0)
        isSection, junk = at.isSectionName(p.h, i)
        if isSection:
            return False # A section definition node.
        elif at.sentinels or at.toString:
            # @ignore must not stop expansion here!
            return True
        elif p.isAtIgnoreNode():
            g.error('did not write @ignore node', p.v.h)
            return False
        elif p.isAtCleanNode():
            p.v.setVisited()
                # # 525: Nested @clean.
                # Suppress a future error. Requires other changes.
            return False
        else:
            return True
    #@+node:ekr.20041005105605.174: *6* at.putCodeLine
    def putCodeLine(self, s, i):
        '''Put a normal code line.'''
        at = self
        # Put @verbatim sentinel if required.
        k = g.skip_ws(s, i)
        if g.match(s, k, self.startSentinelComment + '@'):
            self.putSentinel('@verbatim')
        j = g.skip_line(s, i)
        line = s[i: j]
        # Don't put any whitespace in otherwise blank lines.
        if len(line) > 1: # Preserve *anything* the user puts on the line!!!
            if not at.raw:
                at.putIndent(at.indent, line)
            if line[-1:] == '\n':
                at.os(line[: -1])
                at.onl()
            else:
                at.os(line)
        elif line and line[-1] == '\n':
            at.onl()
        elif line:
            at.os(line) # Bug fix: 2013/09/16
        else:
            g.trace('Can not happen: completely empty line')
    #@+node:ekr.20041005105605.176: *6* at.putRefLine & helpers
    def putRefLine(self, s, i, n1, n2, name, p):
        """Put a line containing one or more references."""
        at = self
        ref = at.findReference(name, p)
        if not ref:
            if hasattr(at, 'allow_undefined_refs'):
                # Allow apparent section reference: just write the line.
                at.putCodeLine(s, i)
            return
        # Compute delta only once.
        junk, delta = g.skip_leading_ws_with_indent(s, i, at.tab_width)
        # Write the lead-in sentinel only once.
        at.putLeadInSentinel(s, i, n1, delta)
        self.putRefAt(name, ref, delta)
        while 1:
            progress = i
            i = n2
            name, n1, n2 = at.findSectionName(s, i)
            if name:
                ref = at.findReference(name, p)
                    # Issues error if not found.
                if ref:
                    middle_s = s[i:n1]
                    self.putAfterMiddleRef(middle_s, delta)
                    self.putRefAt(name, ref, delta)
            else: break
            assert progress < i
        self.putAfterLastRef(s, i, delta)
    #@+node:ekr.20131224085853.16443: *7* at.findReference
    def findReference(self, name, p):
        '''Find a reference to name.  Raise an error if not found.'''
        at = self
        ref = g.findReference(name, p)
        if not ref and not hasattr(at, 'allow_undefined_refs'):
            # Do give this error even if unit testing.
            at.writeError(
                "undefined section: %s\n\treferenced from: %s" % (
                    g.truncate(name, 60), g.truncate(p.h, 60)))
        return ref
    #@+node:ekr.20041005105605.199: *7* at.findSectionName
    def findSectionName(self, s, i):
        '''
        Return n1, n2 representing a section name.
        The section name, *including* brackes is s[n1:n2]
        '''
        end = s.find('\n', i)
        if end == -1:
            n1 = s.find("<<", i)
            n2 = s.find(">>", i)
        else:
            n1 = s.find("<<", i, end)
            n2 = s.find(">>", i, end)
        ok = -1 < n1 < n2
        if ok:
            # Warn on extra brackets.
            for ch, j in (('<', n1 + 2), ('>', n2 + 2)):
                if g.match(s, j, ch):
                    line = g.get_line(s, i)
                    g.es('dubious brackets in', line)
                    break
            name = s[n1:n2+2]
            return name, n1, n2+2
        else:
            return None, n1, len(s)
    #@+node:ekr.20041005105605.178: *7* at.putAfterLastRef
    def putAfterLastRef(self, s, start, delta):
        """Handle whatever follows the last ref of a line."""
        at = self
        j = g.skip_ws(s, start)
        if j < len(s) and s[j] != '\n':
            # Temporarily readjust delta to make @afterref look better.
            at.indent += delta
            at.putSentinel("@afterref")
            end = g.skip_line(s, start)
            after = s[start: end]
            at.os(after)
            if at.sentinels and after and after[-1] != '\n':
                at.onl() # Add a newline if the line didn't end with one.
            at.indent -= delta
    #@+node:ekr.20041005105605.179: *7* at.putAfterMiddleRef
    def putAfterMiddleRef(self, s, delta):
        """Handle whatever follows a ref that is not the last ref of a line."""
        at = self
        if s:
            at.indent += delta
            at.putSentinel("@afterref")
            at.os(s)
            at.onl_sent() # Not a real newline.
            at.indent -= delta
    #@+node:ekr.20041005105605.177: *7* at.putRefAt
    def putRefAt(self, name, ref, delta):
        at = self
        # Fix #132: Section Reference causes clone...
        # https://github.com/leo-editor/leo-editor/issues/132
        # Never put any @+middle or @-middle sentinels.
        at.indent += delta
        at.putSentinel("@+" + name)
        at.putOpenNodeSentinel(ref)
        at.putBody(ref)
        at.putCloseNodeSentinel(ref)
        at.putSentinel("@-" + name)
        at.indent -= delta
    #@+node:ekr.20041005105605.180: *5* writing doc lines...
    #@+node:ekr.20041005105605.181: *6* at.putBlankDocLine
    def putBlankDocLine(self):
        at = self
        at.putPending(split=False)
        if not at.endSentinelComment:
            at.putIndent(at.indent)
            at.os(at.startSentinelComment); at.oblank()
        at.onl()
    #@+node:ekr.20041005105605.183: *6* at.putDocLine
    def putDocLine(self, s, i):
        """
        Handle one line of a doc part.

        Output complete lines and split long lines and queue pending lines.
        Inserted newlines are always preceded by whitespace.
        """
        at = self
        j = g.skip_line(s, i)
        s = s[i: j]
        # if at.endSentinelComment:
            # leading = at.indent
        # else:
            # leading = at.indent + len(at.startSentinelComment) + 1
        if not s or s[0] == '\n':
            # A blank line.
            at.putBlankDocLine()
        else:
            # Write the line as it is.
            at.putIndent(at.indent)
            if not at.endSentinelComment:
                at.os(at.startSentinelComment)
                at.oblank()
            at.os(s)
            if not s.endswith('\n'):
                at.onl()
    #@+node:ekr.20041005105605.185: *6* at.putEndDocLine
    def putEndDocLine(self):
        """Write the conclusion of a doc part."""
        at = self
        at.putPending(split=False)
        # Put the closing delimiter if we are using block comments.
        if at.endSentinelComment:
            at.putIndent(at.indent)
            at.os(at.endSentinelComment)
            at.onl() # Note: no trailing whitespace.
    #@+node:ekr.20041005105605.186: *6* at.putPending (old only)
    def putPending(self, split):
        """Write the pending part of a doc part.

        We retain trailing whitespace iff the split flag is True."""
        at = self
        s = ''.join(at.pending); at.pending = []
        # Remove trailing newline temporarily.  We'll add it back later.
        if s and s[-1] == '\n':
            s = s[: -1]
        if not split:
            s = s.rstrip()
            if not s:
                return
        at.putIndent(at.indent)
        if not at.endSentinelComment:
            at.os(at.startSentinelComment); at.oblank()
        at.os(s); at.onl()
    #@+node:ekr.20041005105605.182: *6* at.putStartDocLine
    def putStartDocLine(self, s, i, kind):
        """Write the start of a doc part."""
        at = self
        at.docKind = kind
        sentinel = "@+doc" if kind == at.docDirective else "@+at"
        directive = "@doc" if kind == at.docDirective else "@"
        # Put whatever follows the directive in the sentinel.
        # Skip past the directive.
        i += len(directive)
        j = g.skip_to_end_of_line(s, i)
        follow = s[i: j]
        # Put the opening @+doc or @-doc sentinel, including whatever follows the directive.
        at.putSentinel(sentinel + follow)
        # Put the opening comment if we are using block comments.
        if at.endSentinelComment:
            at.putIndent(at.indent)
            at.os(at.startSentinelComment); at.onl()
    #@+node:ekr.20041005105605.187: *4* Writing 4,x sentinels...
    #@+node:ekr.20041005105605.188: *5* at.nodeSentinelText & helper
    def nodeSentinelText(self, p):
        """Return the text of a @+node or @-node sentinel for p."""
        at = self
        h = at.removeCommentDelims(p)
        if getattr(at, 'at_shadow_test_hack', False):
            # A hack for @shadow unit testing.
            # see AtShadowTestCase.makePrivateLines.
            return h
        else:
            gnx = p.v.fileIndex
            level = 1 + p.level() - self.root.level()
            stars = '*' * level
            if 1: # Put the gnx in the traditional place.
                if level > 2:
                    return "%s: *%s* %s" % (gnx, level, h)
                else:
                    return "%s: %s %s" % (gnx, stars, h)
            else: # Hide the gnx to the right.
                pad = max(1, 100 - len(stars) - len(h)) * ' '
                return '%s %s%s::%s' % (stars, h, pad, gnx)
    #@+node:ekr.20041005105605.189: *6* at.removeCommentDelims
    def removeCommentDelims(self, p):
        '''
        If the present @language/@comment settings do not specify a single-line comment
        we remove all block comment delims from h. This prevents headline text from
        interfering with the parsing of node sentinels.
        '''
        at = self
        start = at.startSentinelComment
        end = at.endSentinelComment
        h = p.h
        if end:
            h = h.replace(start, "")
            h = h.replace(end, "")
        return h
    #@+node:ekr.20041005105605.190: *5* at.putLeadInSentinel
    def putLeadInSentinel(self, s, i, j, delta):
        """
        Set at.leadingWs as needed for @+others and @+<< sentinels.

        i points at the start of a line.
        j points at @others or a section reference.
        delta is the change in at.indent that is about to happen and hasn't happened yet.
        """
        at = self
        at.leadingWs = "" # Set the default.
        if i == j:
            return # The @others or ref starts a line.
        k = g.skip_ws(s, i)
        if j == k:
            # Only whitespace before the @others or ref.
            at.leadingWs = s[i: j] # Remember the leading whitespace, including its spelling.
        else:
            self.putIndent(at.indent) # 1/29/04: fix bug reported by Dan Winkler.
            at.os(s[i: j])
            at.onl_sent()
    #@+node:ekr.20041005105605.191: *5* at.putCloseNodeSentinel
    def putCloseNodeSentinel(self, p):
        '''End a node.'''
        at = self
        at.raw = False # Bug fix: 2010/07/04
    #@+node:ekr.20041005105605.192: *5* at.putOpenLeoSentinel 4.x
    def putOpenLeoSentinel(self, s):
        """Write @+leo sentinel."""
        at = self
        if at.sentinels or hasattr(at, 'force_sentinels'):
            s = s + "-thin"
            encoding = at.encoding.lower()
            if encoding != "utf-8":
                # New in 4.2: encoding fields end in ",."
                s = s + "-encoding=%s,." % (encoding)
            at.putSentinel(s)
    #@+node:ekr.20041005105605.193: *5* at.putOpenNodeSentinel
    def putOpenNodeSentinel(self, p, inAtAll=False):
        """Write @+node sentinel for p."""
        at = self
        if not inAtAll and p.isAtFileNode() and p != at.root and not at.toString:
            at.writeError("@file not valid in: " + p.h)
            return
        s = at.nodeSentinelText(p)
        at.putSentinel("@+node:" + s)
        # Leo 4.7 b2: we never write tnodeLists.
    #@+node:ekr.20041005105605.194: *5* at.putSentinel (applies cweb hack) 4.x
    # This method outputs all sentinels.

    def putSentinel(self, s):
        "Write a sentinel whose text is s, applying the CWEB hack if needed."
        at = self
        if at.sentinels or hasattr(at, 'force_sentinels'):
            at.putIndent(at.indent)
            at.os(at.startSentinelComment)
            # apply the cweb hack to s. If the opening comment delim ends in '@',
            # double all '@' signs except the first.
            start = at.startSentinelComment
            if start and start[-1] == '@':
                s = s.replace('@', '@@')[1:]
            at.os(s)
            if at.endSentinelComment:
                at.os(at.endSentinelComment)
            at.onl()
    #@+node:ekr.20041005105605.196: *4* Writing 4.x utils...
    #@+node:ekr.20181024134823.1: *5* at.addAtIgnore
    def addAtIgnore(self, root):
        '''Add an @ignore directive to the root node.'''
        if not root:
            g.error('can not happen, no root')
            return
        if root.isAtIgnoreNode():
            g.trace('already contains @ignore', root.h)
        elif not g.unitTesting:
            s = root.b.rstrip()
            if s:
                root.b = s + '\n@ignore\n'
            else:
                root.b = '@ignore\n'
            # The dirty bit may be cleared later.
            root.setDirty()
            g.es('adding @ignore to', root.h)
    #@+node:ekr.20090514111518.5661: *5* at.checkPythonCode & helpers
    def checkPythonCode(self, root, s=None, targetFn=None, pyflakes_errors_only=False):
        '''Perform python-related checks on root.'''
        at = self
        if not targetFn:
            targetFn = at.targetFileName
        if targetFn and targetFn.endswith('.py') and at.checkPythonCodeOnWrite:
            if not s:
                s = at.outputContents
                if not s: return
            # It's too slow to check each node separately.
            if pyflakes_errors_only:
                ok = True
            else:
                ok = at.checkPythonSyntax(root, s)
            # Syntax checking catches most indentation problems.
                # if ok: at.tabNannyNode(root,s)
            if ok and at.runPyFlakesOnWrite and not g.unitTesting:
                ok2 = self.runPyflakes(root, pyflakes_errors_only=pyflakes_errors_only)
            else:
                ok2 = True
            if not ok or not ok2:
                g.app.syntax_error_files.append(g.shortFileName(targetFn))
    #@+node:ekr.20090514111518.5663: *6* at.checkPythonSyntax
    def checkPythonSyntax(self, p, body, supress=False):
        at = self
        try:
            ok = True
            if not g.isPython3:
                body = g.toEncodedString(body)
            body = body.replace('\r', '')
            fn = '<node: %s>' % p.h
            compile(body + '\n', fn, 'exec')
        except SyntaxError:
            if not supress:
                at.syntaxError(p, body)
            ok = False
        except Exception:
            g.trace("unexpected exception")
            g.es_exception()
            ok = False
        return ok
    #@+node:ekr.20090514111518.5666: *7* at.syntaxError (leoAtFile)
    def syntaxError(self, p, body):
        '''Report a syntax error.'''
        g.error("Syntax error in: %s" % (p.h))
        typ, val, tb = sys.exc_info()
        message = hasattr(val, 'message') and val.message
        if message: g.es_print(message)
        if val is None: return
        lines = g.splitLines(body)
        n = val.lineno
        offset = val.offset or 0
        if n is None: return
        i = val.lineno - 1
        for j in range(max(0, i - 2), min(i + 2, len(lines) - 1)):
            if j == i:
                mark = '*'
                node_link = "%s,-%d" % (
                    p.get_UNL(with_proto=True, with_count=True), j+1)
            else:
                mark = ' '
                node_link = None
            text = '%5s:%s %s' % (j+1, mark, lines[j].rstrip())
            g.es_print(text, nodeLink=node_link)
            if j == i:
                g.es_print(' ' * (7 + offset) + '^')
    #@+node:ekr.20161021084954.1: *6* at.runPyflakes
    def runPyflakes(self, root, pyflakes_errors_only):
        '''Run pyflakes on the selected node.'''
        try:
            import leo.commands.checkerCommands as checkerCommands
            if checkerCommands.pyflakes:
                x = checkerCommands.PyflakesCommand(self.c)
                ok = x.run(p=root,pyflakes_errors_only=pyflakes_errors_only)
                return ok
            else:
                return True # Suppress error if pyflakes can not be imported.
        except Exception:
            g.es_exception()
    #@+node:ekr.20090514111518.5665: *6* at.tabNannyNode
    def tabNannyNode(self, p, body, suppress=False):
        import parser
        import tabnanny
        import tokenize
        try:
            readline = g.ReadLinesClass(body).next
            tabnanny.process_tokens(tokenize.generate_tokens(readline))
        except parser.ParserError:
            junk, msg, junk = sys.exc_info()
            if suppress:
                raise
            else:
                g.error("ParserError in", p.h)
                g.es('', str(msg))
        except IndentationError:
            junk, msg, junk = sys.exc_info()
            if suppress:
                raise
            else:
                g.error("IndentationError in", p.h)
                g.es('', str(msg))
        except tokenize.TokenError:
            junk, msg, junk = sys.exc_info()
            if suppress:
                raise
            else:
                g.error("TokenError in", p.h)
                g.es('', str(msg))
        except tabnanny.NannyNag:
            junk, nag, junk = sys.exc_info()
            if suppress:
                raise
            else:
                badline = nag.get_lineno()
                line = nag.get_line()
                message = nag.get_msg()
                g.error("indentation error in", p.h, "line", badline)
                g.es(message)
                line2 = repr(str(line))[1: -1]
                g.es("offending line:\n", line2)
        except Exception:
            g.trace("unexpected exception")
            g.es_exception()
            if suppress: raise
    #@+node:ekr.20080712150045.3: *5* at.closeStringFile
    def closeStringFile(self, theFile):
        at = self
        if theFile:
            theFile.flush()
            s = at.stringOutput = theFile.get()
            at.outputContents = s
            theFile.close()
            at.outputFile = None
            at.outputFileName = g.u('')
            at.shortFileName = ''
            at.targetFileName = None
            return s
        else:
            return None
    #@+node:ekr.20041005105605.135: *5* at.closeWriteFile
    # 4.0: Don't use newline-pending logic.

    def closeWriteFile(self):
        at = self
        if at.outputFile:
            at.outputFile.flush()
            at.outputContents = at.outputFile.get()
            if at.toString:
                at.stringOutput = at.outputFile.get()
            at.outputFile.close()
            at.outputFile = None
            return at.stringOutput
        else:
            return None
    #@+node:ekr.20041005105605.197: *5* at.compareFiles
    def compareFiles(self, path1, path2, ignoreLineEndings, ignoreBlankLines=False):
        """Compare two text files."""
        at = self
        # We can't use 'U' mode because of encoding issues (Python 2.x only).
        s1 = at.outputContents
        e1 = at.encoding
        if s1 is None:
            g.internalError('empty compare file: %s' % path1)
            return False
        s2 = g.readFileIntoEncodedString(path2)
        e2 = None
        if s2 is None:
            g.internalError('empty compare file: %s' % path2)
            return False
        # 2013/10/28: fix bug #1243855: @auto-rst doesn't save text
        # Make sure both strings are unicode.
        # This is requred to handle binary files in Python 3.x.
        if not g.isUnicode(s1):
            s1 = g.toUnicode(s1, encoding=e1)
        if not g.isUnicode(s2):
            s2 = g.toUnicode(s2, encoding=e2)
        equal = s1 == s2
        if ignoreBlankLines and not equal:
            s1 = g.removeBlankLines(s1)
            s2 = g.removeBlankLines(s2)
            equal = s1 == s2
        if ignoreLineEndings and not equal:
            # Wrong: equivalent to ignoreBlankLines!
                # s1 = s1.replace('\n','').replace('\r','')
                # s2 = s2.replace('\n','').replace('\r','')
            s1 = s1.replace('\r', '')
            s2 = s2.replace('\r', '')
            equal = s1 == s2
        return equal
    #@+node:ekr.20041005105605.198: *5* at.directiveKind4 (write logic)
    # These patterns exclude constructs such as @encoding.setter or @encoding(whatever)
    # However, they must allow @language python, @nocolor-node, etc.
    at_directive_kind_pattern = re.compile(r'\s*@([\w-]+)\s*')

    def directiveKind4(self, s, i):
        """
        Return the kind of at-directive or noDirective.
        
        Potential simplifications:
        - Using strings instead of constants.
        - Using additional regex's to recognize directives.
        """
        at = self
        n = len(s)
        if i >= n or s[i] != '@':
            j = g.skip_ws(s, i)
            if g.match_word(s, j, "@others"):
                return at.othersDirective
            elif g.match_word(s, j, "@all"):
                return at.allDirective
            else:
                return at.noDirective
        table = (
            ("@all", at.allDirective),
            ("@c", at.cDirective),
            ("@code", at.codeDirective),
            ("@doc", at.docDirective),
            ("@end_raw", at.endRawDirective),
            ("@others", at.othersDirective),
            ("@raw", at.rawDirective),
            ("@verbatim", at.startVerbatim))
        # Rewritten 6/8/2005.
        if i + 1 >= n or s[i + 1] in (' ', '\t', '\n'):
            # Bare '@' not recognized in cweb mode.
            return at.noDirective if at.language == "cweb" else at.atDirective
        if not s[i + 1].isalpha():
            return at.noDirective # Bug fix: do NOT return miscDirective here!
        if at.language == "cweb" and g.match_word(s, i, '@c'):
            return at.noDirective
        for name, directive in table:
            if g.match_word(s, i, name):
                return directive
        # Support for add_directives plugin.
        # Use regex to properly distinguish between Leo directives
        # and python decorators.
        s2 = s[i:]
        m = self.at_directive_kind_pattern.match(s2)
        if m:
            word = m.group(1)
            if word not in g.globalDirectiveList:
                return at.noDirective
            s3 = s2[m.end(1):]
            if s3 and s3[0] in ".(":
                return at.noDirective
            else:
                return at.miscDirective
        return at.noDirective
    #@+node:ekr.20041005105605.200: *5* at.isSectionName
    # returns (flag, end). end is the index of the character after the section name.

    def isSectionName(self, s, i):
        # 2013/08/01: bug fix: allow leading periods.
        while i < len(s) and s[i] == '.':
            i += 1
        if not g.match(s, i, "<<"):
            return False, -1
        i = g.find_on_line(s, i, ">>")
        if i > -1:
            return True, i + 2
        else:
            return False, -1
    #@+node:ekr.20080712150045.2: *5* at.openStringFile
    def openStringFile(self, fn, encoding='utf-8'):
        at = self
        at.shortFileName = g.shortFileName(fn)
        at.outputFileName = "<string: %s>" % at.shortFileName
        at.outputFile = g.FileLikeObject(encoding=encoding)
        at.targetFileName = "<string-file>"
        return at.outputFile
    #@+node:ekr.20041005105605.201: *5* at.os and allies
    # Note:  self.outputFile may be either a FileLikeObject or a real file.
    #@+node:ekr.20041005105605.202: *6* at.oblank, oblanks & otabs
    def oblank(self):
        self.os(' ')

    def oblanks(self, n):
        self.os(' ' * abs(n))

    def otabs(self, n):
        self.os('\t' * abs(n))
    #@+node:ekr.20041005105605.203: *6* at.onl & onl_sent
    def onl(self):
        """Write a newline to the output stream."""
        self.os('\n') # not self.output_newline

    def onl_sent(self):
        """Write a newline to the output stream, provided we are outputting sentinels."""
        if self.sentinels:
            self.onl()
    #@+node:ekr.20041005105605.204: *6* at.os
    def os(self, s):
        """Write a string to the output stream.

        All output produced by leoAtFile module goes here.
        """
        at = self
        tag = self.underindentEscapeString
        f = at.outputFile
        assert isinstance(f, g.FileLikeObject), f
        if s and f:
            try:
                if s.startswith(tag):
                    junk, s = self.parseUnderindentTag(s)
                # Bug fix: this must be done last.
                # Convert everything to unicode.
                # We expect plain text coming only from sentinels.
                if not g.isUnicode(s):
                    s = g.toUnicode(s, 'ascii')
                f.write(s)
            except Exception:
                at.exception("exception writing:" + s)
    #@+node:ekr.20041005105605.205: *5* at.outputStringWithLineEndings
    # Write the string s as-is except that we replace '\n' with the proper line ending.

    def outputStringWithLineEndings(self, s):
        at = self
        # Calling self.onl() runs afoul of queued newlines.
        if g.isPython3:
            s = g.ue(s, at.encoding)
        s = s.replace('\n', at.output_newline)
        self.os(s)
    #@+node:ekr.20050506090446.1: *5* at.putAtFirstLines
    def putAtFirstLines(self, s):
        '''Write any @firstlines from string s.
        These lines are converted to @verbatim lines,
        so the read logic simply ignores lines preceding the @+leo sentinel.'''
        at = self; tag = "@first"
        i = 0
        while g.match(s, i, tag):
            i += len(tag)
            i = g.skip_ws(s, i)
            j = i
            i = g.skip_to_end_of_line(s, i)
            # Write @first line, whether empty or not
            line = s[j: i]
            at.os(line); at.onl()
            i = g.skip_nl(s, i)
    #@+node:ekr.20050506090955: *5* at.putAtLastLines
    def putAtLastLines(self, s):
        '''Write any @last lines from string s.
        These lines are converted to @verbatim lines,
        so the read logic simply ignores lines following the @-leo sentinel.'''
        at = self; tag = "@last"
        # Use g.splitLines to preserve trailing newlines.
        lines = g.splitLines(s)
        n = len(lines); j = k = n - 1
        # Scan backwards for @last directives.
        while j >= 0:
            line = lines[j]
            if g.match(line, 0, tag): j -= 1
            elif not line.strip():
                j -= 1
            else: break
        # Write the @last lines.
        for line in lines[j + 1: k + 1]:
            if g.match(line, 0, tag):
                i = len(tag); i = g.skip_ws(line, i)
                at.os(line[i:])
    #@+node:ekr.20041005105605.206: *5* at.putDirective 4.x & helper
    def putDirective(self, s, i):
        r'''
        Output a sentinel a directive or reference s.

        It is important for PHP and other situations that \@first and \@last
        directives get translated to verbatim lines that do *not* include what
        follows the @first & @last directives.
        '''
        at = self
        k = i
        j = g.skip_to_end_of_line(s, i)
        directive = s[i: j]
        if g.match_word(s, k, "@delims"):
            at.putDelims(directive, s, k)
        elif g.match_word(s, k, "@language"):
            self.putSentinel("@" + directive)
        elif g.match_word(s, k, "@comment"):
            self.putSentinel("@" + directive)
        elif g.match_word(s, k, "@last"):
            self.putSentinel("@@last")
                # Convert to an verbatim line _without_ anything else.
        elif g.match_word(s, k, "@first"):
            self.putSentinel("@@first")
                # Convert to an verbatim line _without_ anything else.
        else:
            self.putSentinel("@" + directive)
        i = g.skip_line(s, k)
        return i
    #@+node:ekr.20041005105605.207: *6* at.putDelims
    def putDelims(self, directive, s, k):
        '''Put an @delims directive.'''
        at = self
        # Put a space to protect the last delim.
        at.putSentinel(directive + " ") # 10/23/02: put @delims, not @@delims
        # Skip the keyword and whitespace.
        j = i = g.skip_ws(s, k + len("@delims"))
        # Get the first delim.
        while i < len(s) and not g.is_ws(s[i]) and not g.is_nl(s, i):
            i += 1
        if j < i:
            at.startSentinelComment = s[j: i]
            # Get the optional second delim.
            j = i = g.skip_ws(s, i)
            while i < len(s) and not g.is_ws(s[i]) and not g.is_nl(s, i):
                i += 1
            at.endSentinelComment = s[j: i] if j < i else ""
        else:
            at.writeError("Bad @delims directive")
    #@+node:ekr.20041005105605.210: *5* at.putIndent
    def putIndent(self, n, s=''):
        """Put tabs and spaces corresponding to n spaces,
        assuming that we are at the start of a line.

        Remove extra blanks if the line starts with the underindentEscapeString"""
        tag = self.underindentEscapeString
        if s.startswith(tag):
            n2, s2 = self.parseUnderindentTag(s)
            if n2 >= n: return
            elif n > 0: n -= n2
            else: n += n2
        if n > 0:
            w = self.tab_width
            if w > 1:
                q, r = divmod(n, w)
                self.otabs(q)
                self.oblanks(r)
            else:
                self.oblanks(n)
    #@+node:ekr.20041005105605.211: *5* at.putInitialComment
    def putInitialComment(self):
        c = self.c
        s2 = c.config.output_initial_comment
        if s2:
            lines = s2.split("\\n")
            for line in lines:
                line = line.replace("@date", time.asctime())
                if line:
                    self.putSentinel("@comment " + line)
    #@+node:ekr.20080712150045.1: *5* at.replaceFileWithString
    def replaceFileWithString(self, fn, s):
        '''
        Replace the file with s if s is different from theFile's contents.

        Return True if theFile was changed.

        This is used only by the @shadow logic.
        '''
        at, c = self, self.c
        exists = g.os_path_exists(fn)
        if exists: # Read the file.  Return if it is the same.
            s2, e = g.readFileIntoString(fn)
            if s is None:
                return False
            if s == s2:
                report = c.config.getBool('report-unchanged-files', default=True)
                if report and not g.unitTesting:
                    g.es('unchanged:', fn)
                return False
        # Issue warning if directory does not exist.
        theDir = g.os_path_dirname(fn)
        if theDir and not g.os_path_exists(theDir):
            if not g.unitTesting:
                g.error('not written: %s directory not found' % fn)
            return False
        # Replace
        try:
            f = open(fn, 'wb')
            # 2013/10/28: Fix bug 1243847: unicode error when saving @shadow nodes.
            # Call g.toEncodedString regardless of Python version.
            s = g.toEncodedString(s, encoding=self.encoding)
            f.write(s)
            f.close()
            if g.unitTesting:
                pass
            else:
                if exists:
                    g.es('wrote:    ', fn)
                else:
                    g.es('created:', fn)
            return True
        except IOError:
            at.error('unexpected exception writing file: %s' % (fn))
            g.es_exception()
            return False
    #@+node:ekr.20041005105605.212: *5* at.replaceTargetFileIfDifferent
    def replaceTargetFileIfDifferent(self, root, ignoreBlankLines=False):
        '''Create target file as follows:
        1. If target file does not exist, rename output file to target file.
        2. If target file is identical to output file, remove the output file.
        3. If target file is different from output file,
           remove target file, then rename output file to be target file.

        Return True if the original file was changed.
        '''
        at = self; c = at.c
        if at.toString:
            # Do *not* change the actual file or set any dirty flag.
            at.fileChangedFlag = False
            return False
        if root:
            root.clearDirty()
        # Fix bug 1132821: Leo replaces a soft link with a real file.
        if at.outputFileName:
            at.outputFileName = g.os_path_realpath(at.outputFileName)
        if at.targetFileName:
            at.targetFileName = g.os_path_realpath(at.targetFileName)
        # #531: Optionally report timestamp...
        if c.config.getBool('log-show-save-time', default=False):
            format = c.config.getString('log-timestamp-format') or "%H:%M:%S"
            timestamp = time.strftime(format) + ' '
        else:
            timestamp = ''
        if g.os_path_exists(at.targetFileName):
            if at.compareFiles(
                at.outputFileName,
                at.targetFileName,
                ignoreLineEndings=not at.explicitLineEnding,
                ignoreBlankLines=ignoreBlankLines
            ):
                # Files are identical.
                report = c.config.getBool('report-unchanged-files', default=True)
                at.sameFiles += 1
                if report and not g.unitTesting:
                    g.es('%sunchanged: %s' % (timestamp, at.shortFileName))
                at.fileChangedFlag = False
                # Leo 5.6: Check unchanged files.
                at.checkPythonCode(root, pyflakes_errors_only=True)
                return False
            else:
                # A mismatch. Report if the files differ only in line endings.
                if (
                    at.explicitLineEnding and
                    at.compareFiles(
                        at.outputFileName,
                        at.targetFileName,
                        ignoreLineEndings=True)
                ):
                    g.warning("correcting line endings in:", at.targetFileName)
                s = at.outputContents
                ok = at.create(at.targetFileName, s)
                if ok:
                    c.setFileTimeStamp(at.targetFileName)
                    if not g.unitTesting:
                        g.es('%swrote: %s' % (timestamp, at.shortFileName))
                else:
                    g.error('error writing', at.shortFileName)
                    g.es('not written:', at.shortFileName)
                    at.addAtIgnore(root)
                at.checkPythonCode(root)
                    # Bug fix: check *after* writing the file.
                at.fileChangedFlag = ok
                return ok
        else:
            s = at.outputContents
            ok = self.create(at.targetFileName, s)
            if ok:
                c.setFileTimeStamp(at.targetFileName)
                if not g.unitTesting:
                    g.es('%screated: %s' % (timestamp, at.targetFileName))
                if root:
                    # Fix bug 889175: Remember the full fileName.
                    at.rememberReadPath(at.targetFileName, root)
            else:
                # at.rename gives the error.
                at.addAtIgnore(root)
            # No original file to change. Return value tested by a unit test.
            at.fileChangedFlag = False
            at.checkPythonCode(root)
            return False
    #@+node:ekr.20041005105605.216: *5* at.warnAboutOrpanAndIgnoredNodes
    # Called from writeOpenFile.

    def warnAboutOrphandAndIgnoredNodes(self):
        # Always warn, even when language=="cweb"
        at, root = self, self.root
        if at.errors:
            return # No need to repeat this.
        for p in root.self_and_subtree(copy=False):
            if not p.v.isVisited():
                at.writeError("Orphan node:  " + p.h)
                if p.hasParent():
                    g.blue("parent node:", p.parent().h)
        p = root.copy()
        after = p.nodeAfterTree()
        while p and p != after:
            if p.isAtAllNode():
                p.moveToNodeAfterTree()
            else:
                if p.isAtIgnoreNode():
                    at.writeError("@ignore node: " + p.h)
                p.moveToThreadNext()
    #@+node:ekr.20041005105605.217: *5* at.writeError
    def writeError(self, message=None):
        '''Issue an error while writing an @<file> node.'''
        at = self
        if at.errors == 0:
            g.es_error("errors writing: " + at.targetFileName)
        at.error(message)
        at.addAtIgnore(at.root)
    #@+node:ekr.20041005105605.218: *5* at.writeException
    def writeException(self, root=None):
        at = self
        g.error("exception writing:", at.targetFileName)
        g.es_exception()
        if at.outputFile:
            at.outputFile.flush()
            at.outputFile.close()
            at.outputFile = None
        if at.outputFileName:
            at.remove(at.outputFileName)
        at.addAtIgnore(at.root)
    #@+node:ekr.20041005105605.219: *3* at.Utilites
    #@+node:ekr.20041005105605.220: *4* at.error & printError
    def error(self, *args):
        at = self
        if True: # args:
            at.printError(*args)
        at.errors += 1

    def printError(self, *args):
        '''Print an error message that may contain non-ascii characters.'''
        at = self
        if at.errors:
            g.error(*args)
        else:
            g.warning(*args)
    #@+node:ekr.20041005105605.221: *4* at.exception
    def exception(self, message):
        self.error(message)
        g.es_exception()
    #@+node:ekr.20050104131929: *4* at.file operations...
    #@+at The difference, if any, between these methods and the corresponding g.utils_x
    # functions is that these methods may call self.error.
    #@+node:ekr.20050104131820: *5* at.chmod
    def chmod(self, fileName, mode):
        # Do _not_ call self.error here.
        return g.utils_chmod(fileName, mode)
    #@+node:ekr.20130910100653.11323: *5* at.create
    def create(self, fn, s):
        '''Create a file whose contents are s.'''
        at = self
        # 2015/07/15: do this before converting to encoded string.
        if at.output_newline != '\n':
            s = s.replace('\r', '').replace('\n', at.output_newline)
        # This is part of the new_write logic.
        # This is the only call to g.toEncodedString in the new_write logic.
        # 2013/10/28: fix bug 1243847: unicode error when saving @shadow nodes
        if g.isUnicode(s):
            s = g.toEncodedString(s, encoding=at.encoding)
        try:
            f = open(fn, 'wb') # Must be 'wb' to preserve line endings.
            f.write(s)
            f.close()
        except Exception:
            f = None
            g.es_exception()
            g.error('error writing', fn)
            g.es('not written:', fn)
        return bool(f)
    #@+node:ekr.20050104131929.1: *5* at.rename
    #@+<< about os.rename >>
    #@+node:ekr.20050104131929.2: *6* << about os.rename >>
    #@+at Here is the Python 2.4 documentation for rename (same as Python 2.3)
    # 
    # Rename the file or directory src to dst.  If dst is a directory, OSError will be raised.
    # 
    # On Unix, if dst exists and is a file, it will be removed silently if the user
    # has permission. The operation may fail on some Unix flavors if src and dst are
    # on different filesystems. If successful, the renaming will be an atomic
    # operation (this is a POSIX requirement).
    # 
    # On Windows, if dst already exists, OSError will be raised even if it is a file;
    # there may be no way to implement an atomic rename when dst names an existing
    # file.
    #@-<< about os.rename >>

    def rename(self, src, dst, mode=None, verbose=True):
        '''
        Remove dst if it exists, then rename src to dst.
        Change the mode of the renamed file if mode is given.
        Return True if all went well.
        '''
        c = self.c
        head, junk = g.os_path_split(dst)
        if head:
            g.makeAllNonExistentDirectories(head, c=c)
        if g.os_path_exists(dst):
            if not self.remove(dst, verbose=verbose):
                return False
        try:
            os.rename(src, dst)
            if mode is not None:
                self.chmod(dst, mode)
            return True
        except Exception:
            if verbose:
                self.error("exception renaming: %s to: %s" % (
                    self.outputFileName, self.targetFileName))
                g.es_exception()
            return False
    #@+node:ekr.20050104132018: *5* at.remove
    def remove(self, fileName, verbose=True):
        if not fileName:
            g.trace('No file name', g.callers())
            return False
        try:
            os.remove(fileName)
            return True
        except Exception:
            if verbose:
                self.error("exception removing: %s" % fileName)
                g.es_exception()
                g.trace(g.callers(5))
            return False
    #@+node:ekr.20050104132026: *5* at.stat
    def stat(self, fileName):
        '''Return the access mode of named file, removing any setuid, setgid, and sticky bits.'''
        # Do _not_ call self.error here.
        return g.utils_stat(fileName)
    #@+node:ekr.20090530055015.6023: *4* at.get/setPathUa
    def getPathUa(self, p):
        if hasattr(p.v, 'tempAttributes'):
            d = p.v.tempAttributes.get('read-path', {})
            return d.get('path')
        else:
            return ''

    def setPathUa(self, p, path):
        if not hasattr(p.v, 'tempAttributes'):
            p.v.tempAttributes = {}
        d = p.v.tempAttributes.get('read-path', {})
        d['path'] = path
        p.v.tempAttributes['read-path'] = d
    #@+node:ekr.20081216090156.4: *4* at.parseUnderindentTag
    # Important: this is part of the *write* logic.
    # It is called from at.os and at.putIndent.

    def parseUnderindentTag(self, s):
        tag = self.underindentEscapeString
        s2 = s[len(tag):]
        # To be valid, the escape must be followed by at least one digit.
        i = 0
        while i < len(s2) and s2[i].isdigit():
            i += 1
        if i > 0:
            n = int(s2[: i])
            # Bug fix: 2012/06/05: remove any period following the count.
            # This is a new convention.
            if i < len(s2) and s2[i] == '.':
                i += 1
            return n, s2[i:]
        else:
            return 0, s
    #@+node:ekr.20090712050729.6017: *4* at.promptForDangerousWrite
    def promptForDangerousWrite(self, fileName, kind, message=None):
        '''Raise a dialog asking the user whether to overwrite an existing file.'''
        at, c, root = self, self.c, self.root
        if g.app.unitTesting:
            val = g.app.unitTestDict.get('promptForDangerousWrite')
            return val in (None, True)
        if at.cancelFlag:
            assert at.canCancelFlag
            return False
        if at.yesToAll:
            assert at.canCancelFlag
            return True
        if root and root.h.startswith('@auto-rst'):
            # Fix bug 50: body text lost switching @file to @auto-rst
            # Refuse to convert any @<file> node to @auto-rst.
            d = root.v.at_read if hasattr(root.v, 'at_read') else {}
            aList = sorted(d.get(fileName, []))
            for h in aList:
                if not h.startswith('@auto-rst'):
                    g.es('can not convert @file to @auto-rst!', color='red')
                    g.es('reverting to:', h)
                    root.h = h
                    c.redraw()
                    return False
        if message is None:
            message = '%s %s\n%s\n%s' % (
                kind, g.splitLongFileName(fileName),
                g.tr('already exists.'),
                g.tr('Overwrite this file?'))
        result = g.app.gui.runAskYesNoCancelDialog(c,
            title='Overwrite existing file?',
            yesToAllMessage="Yes To &All",
            message=message,
            cancelMessage="&Cancel (No To All)",
        )
        if at.canCancelFlag:
            # We are in the writeAll logic so these flags can be set.
            if result == 'cancel':
                at.cancelFlag = True
            elif result == 'yes-to-all':
                at.yesToAll = True
        return result in ('yes', 'yes-to-all')
    #@+node:ekr.20120112084820.10001: *4* at.rememberReadPath
    def rememberReadPath(self, fn, p):
        '''
        Remember the files that have been read *and*
        the full headline (@<file> type) that caused the read.
        '''
        v = p.v
        # Fix bug #50: body text lost switching @file to @auto-rst
        if not hasattr(v, 'at_read'):
            v.at_read = {}
        d = v.at_read
        aSet = d.get(fn, set())
        aSet.add(p.h)
        d[fn] = aSet
    #@+node:ekr.20080923070954.4: *4* at.scanAllDirectives
    def scanAllDirectives(self,
        p,
        forcePythonSentinels=False,
        importing=False,
        issuePathWarning=False,
        reading=False,
    ):
        '''
        Scan p and p's ancestors looking for directives,
        setting corresponding AtFile ivars.
        '''
        at, c = self, self.c
        g.app.atPathInBodyWarning = None
        #@+<< set ivars >>
        #@+node:ekr.20080923070954.14: *5* << Set ivars >> (at.scanAllDirectives)
        at.page_width = c.page_width
        at.tab_width = c.tab_width
        at.default_directory = None # 8/2: will be set later.
        if c.target_language:
            c.target_language = c.target_language.lower()
        delims = g.set_delims_from_language(c.target_language)
        at.language = c.target_language
        at.encoding = c.config.default_derived_file_encoding
        at.output_newline = g.getOutputNewline(c=c) # Init from config settings.
        #@-<< set ivars >>
        lang_dict = {'language': at.language, 'delims': delims,}
        table = (
            ('encoding', at.encoding, g.scanAtEncodingDirectives),
            # ('lang-dict',   lang_dict,      g.scanAtCommentAndAtLanguageDirectives),
            ('lang-dict', None, g.scanAtCommentAndAtLanguageDirectives),
            ('lineending', None, g.scanAtLineendingDirectives),
            ('pagewidth', c.page_width, g.scanAtPagewidthDirectives),
            ('path', None, c.scanAtPathDirectives),
            ('tabwidth', c.tab_width, g.scanAtTabwidthDirectives),
        )
        # Set d by scanning all directives.
        aList = g.get_directives_dict_list(p)
        d = {}
        for key, default, func in table:
            val = func(aList)
            d[key] = default if val is None else val
        # Post process.
        lineending = d.get('lineending')
        lang_dict = d.get('lang-dict')
        if lang_dict:
            delims = lang_dict.get('delims')
            at.language = lang_dict.get('language')
        else:
            # No language directive.  Look for @<file> nodes.
            language = g.getLanguageFromAncestorAtFileNode(p) or 'python'
            delims = g.set_delims_from_language(language)
        at.encoding = d.get('encoding')
        at.explicitLineEnding = bool(lineending)
        at.output_newline = lineending or g.getOutputNewline(c=c)
        at.page_width = d.get('pagewidth')
        at.default_directory = d.get('path')
        at.tab_width = d.get('tabwidth')
        if not importing and not reading:
            # Don't override comment delims when reading!
            #@+<< set comment strings from delims >>
            #@+node:ekr.20080923070954.13: *5* << Set comment strings from delims >> (at.scanAllDirectives)
            if forcePythonSentinels:
                # Force Python language.
                delim1, delim2, delim3 = g.set_delims_from_language("python")
                self.language = "python"
            else:
                delim1, delim2, delim3 = delims
            # Use single-line comments if we have a choice.
            # delim1,delim2,delim3 now correspond to line,start,end
            if delim1:
                at.startSentinelComment = delim1
                at.endSentinelComment = "" # Must not be None.
            elif delim2 and delim3:
                at.startSentinelComment = delim2
                at.endSentinelComment = delim3
            else: # Emergency!
                #
                # Issue an error only if at.language has been set.
                # This suppresses a message from the markdown importer.
                if not g.app.unitTesting and at.language:
                    g.trace(repr(at.language), g.callers())
                    g.es_print("unknown language: using Python comment delimiters")
                    g.es_print("c.target_language:", c.target_language)
                at.startSentinelComment = "#" # This should never happen!
                at.endSentinelComment = ""
            #@-<< set comment strings from delims >>
        # For unit testing.
        d = {
            "all": all,
            "encoding": at.encoding,
            "language": at.language,
            "lineending": at.output_newline,
            "pagewidth": at.page_width,
            "path": at.default_directory,
            "tabwidth": at.tab_width,
        }
        return d
    #@+node:ekr.20120110174009.9965: *4* at.shouldPromptForDangerousWrite
    def shouldPromptForDangerousWrite(self, fn, p):
        '''
        Return True if a prompt should be issued
        when writing p (an @<file> node) to fn.
        '''
        if not g.os_path_exists(fn):
            # No danger of overwriting fn.
            return False
        elif hasattr(p.v, 'at_read'):
            # Fix bug #50: body text lost switching @file to @auto-rst
            d = p.v.at_read
            aSet = d.get(fn, set())
            return p.h not in aSet
        else:
            return True
                # The file was never read.
    #@+node:ekr.20041005105605.20: *4* at.warnOnReadOnlyFile
    def warnOnReadOnlyFile(self, fn):
        # os.access() may not exist on all platforms.
        try:
            read_only = not os.access(fn, os.W_OK)
        except AttributeError:
            read_only = False
        if read_only:
            g.error("read only:", fn)
    #@-others

atFile = AtFile # compatibility
#@+node:ekr.20180602102448.1: ** class FastAtRead
class FastAtRead (object):
    '''
    Read an exteral file, created from an @file tree.
    This is Vitalije's code, edited by EKR.
    '''

    def __init__ (self, c, gnx2vnode, test=False, TestVNode=None): 
        self.c = c
        assert gnx2vnode is not None
        self.gnx2vnode = gnx2vnode
            # The global fc.gnxDict. Keys are gnx's, values are vnodes.
        self.path = None
        self.root = None
        self.VNode = TestVNode if test else leoNodes.VNode
        self.test = test

    #@+others
    #@+node:ekr.20180602103135.3: *3* fast_at.get_patterns
    #@@nobeautify

    def get_patterns(self, delims):
        '''Create regex patterns for the given comment delims.'''
        # This must be a function, because of @comments & @delims.
        delim_start, delim_end = delims
        delims = re.escape(delim_start), re.escape(delim_end or '')
        delim_start, delim_end = delims
        patterns = (
            # The list of patterns, in alphabetical order.
            # These patterns must be mutually exclusive.
            r'^\s*%s@afterref%s$'%delims,               # @afterref
            r'^(\s*)%s@(\+|-)all\b(.*)%s$'%delims,      # @all
            r'^\s*%s@@c(ode)?%s$'%delims,               # @c and @code
            r'^\s*%s@comment(.*)%s'%delims,             # @comment
            r'^\s*%s@delims(.*)%s'%delims,              # @delims
            r'^\s*%s@\+(at|doc)?(\s.*?)?%s\n'%delims,   # @doc or @
            r'^\s*%s@end_raw\s*%s'%delims,              # @end_raw
            r'^\s*%s@@first%s$'%delims,                 # @first
            r'^\s*%s@@last%s$'%delims,                  # @last
            r'^(\s*)%s@\+node:([^:]+): \*(\d+)?(\*?) (.*)%s$'%delims, # @node
            r'^(\s*)%s@(\+|-)others\b(.*)%s$'%delims,   # @others
            r'^\s*%s@raw(.*)%s'%delims,                 # @raw
            r'^(\s*)%s@(\+|-)%s\s*%s$'%(                # section ref
                delim_start, g.angleBrackets('(.*)'), delim_end)
        )
        # Return the compiled patterns, in alphabetical order.
        return (re.compile(pattern) for pattern in patterns)
    #@+node:ekr.20180603060721.1: *3* fast_at.post_pass
    def post_pass(self, gnx2body, gnx2vnode, root_v):
        '''Set all body text.'''
        # Set the body text.
        if self.test:
            # Check the keys.
            bkeys = sorted(gnx2body.keys())
            vkeys = sorted(gnx2vnode.keys())
            if bkeys != vkeys:
                g.trace('KEYS MISMATCH')
                g.printObj(bkeys)
                g.printObj(vkeys)
                if self.test:
                    sys.exit(1)
            # Set the body text.
            for key in vkeys:
                v = gnx2vnode.get(key)
                body = gnx2body.get(key)
                v._bodyString = ''.join(body)
        else:
            assert root_v.gnx in gnx2vnode, root_v
            assert root_v.gnx in gnx2body, root_v
            # Don't use items(): it doesn't exist in Python 2.
            for key in gnx2body: 
                body = gnx2body.get(key)
                v = gnx2vnode.get(key)
                assert v
                v._bodyString = g.toUnicode(''.join(body))
    #@+node:ekr.20180602103135.2: *3* fast_at.scan_header
    header_pattern = re.compile(r'''
        ^(.+)@\+leo
        (-ver=(\d+))?
        (-thin)?
        (-encoding=(.*)(\.))?
        (.*)$''', re.VERBOSE)

    def scan_header(self, lines):
        '''
        Scan for the header line, which follows any @first lines.
        Return (delims, first_lines, i+1) or None
        '''
        first_lines = []
        i = 0 # To keep pylint happy.
        for i, line in enumerate(lines):
            m = self.header_pattern.match(line)
            if m:
                delims = m.group(1), m.group(8) or ''
                return delims, first_lines, i+1
            first_lines.append(line)
        return None
    #@+node:ekr.20180602103135.8: *3* fast_at.scan_lines
    def scan_lines(self, delims, first_lines, lines, start, test=False):
        '''Scan all lines of the file, creating vnodes.'''
        #@+<< init scan_lines >>
        #@+node:ekr.20180602103135.9: *4* << init scan_lines >>
        #
        # Simple vars...
        afterref = False
            # A special verbatim line follows @afterref.
        clone_v = None
            # The root of the clone tree.
            # When not None, we are scanning a clone and all it's descendants.
        delim_start, delim_end = delims
            # The start/end delims.
        doc_skip = (delim_start + '\n', delim_end + '\n')
            # To handle doc parts.
        first_i = 0
            # Index into first array.
           
        in_doc = False
            # True: in @doc parts.
        in_raw = False
            # True: @raw seen.
        is_cweb = delim_start == '@q@' and delim_end == '@>'
            # True: cweb hack in effect.
        indent = 0 
            # The current indentation.
        level_stack = []
            # Entries are (vnode, in_clone_tree)
        n_last_lines = 0
            # The number of @@last directives seen.
        sentinel = delim_start + '@'
            # Faster than a regex!
        stack = []
            # Entries are (gnx, indent, body)
            # Updated when at+others, at+<section>, or at+all is seen.
        verbline = delim_start + '@verbatim' + delim_end + '\n'
            # The spelling of at-verbatim sentinel
        verbatim = False
            # True: the next line must be added without change.
        #
        # Init the data for the root node.
        #

        #
        # Init the parent vnode for testing.
        #
        if self.test:
            root_gnx = gnx = g.u('root-gnx')
                # The node that we are reading.
                # start with the gnx for the @file node.
            gnx_head =  g.u('<hidden top vnode>')
                # The headline of the root node.
            context = None
            parent_v = self.VNode(context=context, gnx=gnx)
            parent_v._headString = gnx_head
                # Corresponds to the @files node itself.
        else:
            # Production.
            root_gnx = gnx = self.root.gnx
            context = self.c
            parent_v = self.root.v
        root_v = parent_v
            # Does not change.
        level_stack.append((root_v, False),)
        #
        # Init the gnx dict last.
        #
        gnx2vnode = self.gnx2vnode
            # Keys are gnx's, values are vnodes.
        gnx2body = {}
            # Keys are gnxs, values are list of body lines.
        gnx2vnode[gnx] = parent_v
            # Add gnx to the keys
        gnx2body[gnx] = body = first_lines
            # Add gnx to the keys.
            # Body is the list of lines presently being accumulated.
        #
        # get the patterns.
        after_pat, all_pat, code_pat, comment_pat, delims_pat,\
        doc_pat, end_raw_pat, first_pat, last_pat, \
        node_start_pat, others_pat, raw_pat, ref_pat = self.get_patterns(delims)
        #@-<< init scan_lines >>
        #@+<< define dump_v >>
        #@+node:ekr.20180613061743.1: *4* << define dump_v >>
        def dump_v():
            '''Dump the level stack and v.'''
            print('----- LEVEL', level, v.h)
            print('       PARENT', parent_v.h)
            print('[')
            for i, data in enumerate(level_stack):
                v2, in_tree = data
                print('%2s %5s %s' % (i+1, in_tree, v2.h))
            print(']')
            print('PARENT.CHILDREN...')
            g.printObj([v2.h for v2 in parent_v.children])
            print('PARENTS...')
            g.printObj([v2.h for v2 in v.parents])
        #@-<< define dump_v >>
        i = 0 # To keep pylint happy.
        for i, line in enumerate(lines[start:]):
            # Order matters.
            #@+<< 1. common code for all lines >>
            #@+node:ekr.20180602103135.10: *4* << 1. common code for all lines >>
            if verbatim:
                # We are in raw mode, or other special situation.
                # Previous line was verbatim sentinel. Append this line as it is.
                if afterref:
                    afterref = False
                    if body: # a List of lines.
                        body[-1] = body[-1].rstrip() + line
                    else:
                        body = [line]
                    verbatim = False
                elif in_raw:
                    m = end_raw_pat.match(line)
                    if m:
                        in_raw = False
                        verbatim = False
                    else:
                         body.append(line)
                         # Continue verbatim/raw mode.
                else:
                    body.append(line)
                    verbatim = False
                continue
            if line == verbline: # <delim>@verbatim.
                verbatim = True
                continue
            #
            # Strip the line only once.
            strip_line = line.strip()
            #
            # Undo the cweb hack.
            if is_cweb and line.startswith(sentinel):
                line = line[:len(sentinel)] + line[len(sentinel):].replace('@@', '@')
            # Adjust indentation.
            if indent and line[:indent].isspace() and len(line) > indent:
                line = line[indent:]
            #@-<< 1. common code for all lines >>
            #@+<< 2. short-circuit later tests >>
            #@+node:ekr.20180602103135.12: *4* << 2. short-circuit later tests >>
            # This is valid because all following sections are either:
            # 1. guarded by 'if in_doc' or
            # 2. guarded by a pattern that matches the start of the sentinel.   
            #
            if not in_doc and not strip_line.startswith(sentinel):
                # lstrip() is faster than using a regex!
                body.append(line)
                continue
            #@-<< 2. short-circuit later tests >>
            #@+<< 3. handle @others >>
            #@+node:ekr.20180602103135.14: *4* << 3. handle @others >>
            m = others_pat.match(line)
            if m:
                in_doc = False
                if m.group(2) == '+': # opening sentinel
                    body.append('%s@others%s\n' % (m.group(1), m.group(3) or ''))
                    stack.append((gnx, indent, body))
                    indent += m.end(1) # adjust current identation
                else: # closing sentinel.
                    # m.group(2) is '-' because the pattern matched.
                    gnx, indent, body = stack.pop()
                continue

            #@-<< 3. handle @others >>
            #@afterref
 # clears in_doc
            #@+<< 4. handle section refs >>
            #@+node:ekr.20180602103135.18: *4* << 4. handle section refs >>
            m = ref_pat.match(line)
            if m:
                in_doc = False
                if m.group(2) == '+':
                    # open sentinel.
                    body.append(m.group(1) + g.angleBrackets(m.group(3)) + '\n')
                    stack.append((gnx, indent, body))
                    indent += m.end(1)
                else:
                    # close sentinel.
                    # m.group(2) is '-' because the pattern matched.
                    gnx, indent, body = stack.pop()
                continue
            #@-<< 4. handle section refs >>
            #@afterref
 # clears in_doc.
            # Order doesn't matter, but match more common sentinels first.
            #@+<< handle node_start >>
            #@+node:ekr.20180602103135.19: *4* << handle node_start >>
            m = node_start_pat.match(line)
            if m:
                in_doc, in_raw = False, False
                gnx, head = m.group(2), m.group(5)
                level = int(m.group(3)) if m.group(3) else 1 + len(m.group(4))
                    # m.group(3) is the level number, m.group(4) is the number of stars.
                v = gnx2vnode.get(gnx)
                #
                # Case 1: The root @file node. Don't change the headline.
                if v and v == root_v:
                    clone_v = None
                    gnx2body[gnx] = body = []
                    v.children = []
                    continue
                #
                # Case 2: We are scanning the descendants of a clone.
                parent_v, clone_v = level_stack[level-2]
                if v and clone_v:
                    # The last version of the body and headline wins..
                    gnx2body[gnx] = body = []
                    v._headString = head
                    # Update the level_stack.
                    level_stack = level_stack[:level-1]
                    level_stack.append((v, clone_v),)
                    # Always clear the children!
                    v.children=[]
                    parent_v.children.append(v)
                    continue
                #
                # Case 3: we are not already scanning the descendants of a clone.
                if v:
                    # The *start* of a clone tree. Reset the children.
                    clone_v = v
                    v.children = []
                else:
                    # Make a new vnode.
                    v = self.VNode(context=context, gnx=gnx)
                #
                # The last version of the body and headline wins.
                gnx2vnode[gnx] = v
                gnx2body[gnx] = body = []
                v._headString = head
                #
                # Update the stack.
                level_stack = level_stack[:level-1]
                level_stack.append((v, clone_v),)
                #
                # Update the links.
                assert v != root_v
                parent_v.children.append(v)
                v.parents.append(parent_v)
                # dump_v()
                continue
            #@-<< handle node_start >>
            #@+<< handle end of @doc & @code parts >>
            #@+node:ekr.20180602103135.16: *4* << handle end of @doc & @code parts >>
            if in_doc:
                # When delim_end exists the doc block:
                # - begins with the opening delim, alonw on its own line
                # - ends with the closing delim, alone on its own line.
                # Both of these lines should be skipped
                if line in doc_skip:
                    # doc_skip is (delim_start + '\n', delim_end + '\n')
                    continue
                #
                # Check for @c or @code.
                m = code_pat.match(line)
                if m:
                    in_doc = False 
                    body.append('@code\n' if m.group(1) else '@c\n')
                    continue
            else:
                m = doc_pat.match(line)
                if m:
                    # @+at or @+doc?
                    doc = '@doc' if m.group(1) == 'doc' else '@'
                    doc2 = m.group(2) or '' # Trailing text.
                    if doc2:
                        body.append('%s%s\n'%(doc, doc2))
                    else:
                        body.append(doc + '\n')
                    # Enter @doc mode.
                    in_doc = True
                    continue
            #@-<< handle end of @doc & @code parts >>
            #@+<< handle @all >>
            #@+node:ekr.20180602103135.13: *4* << handle @all >>
            m = all_pat.match(line)
            if m:
                # @all tells Leo's *write* code not to check for undefined sections.
                # Here, in the read code, we merely need to add it to the body.
                # Pushing and popping the stack may not be necessary, but it can't hurt.
                if m.group(2) == '+': # opening sentinel
                    body.append('%s@all%s\n' % (m.group(1), m.group(3) or ''))
                    stack.append((gnx, indent, body))
                else: # closing sentinel.
                    # m.group(2) is '-' because the pattern matched.
                    gnx, indent, body = stack.pop()
                    gnx2body[gnx] = body
                continue
            #@-<< handle @all >>
            #@+<< handle afterref >>
            #@+node:ekr.20180603063102.1: *4* << handle afterref >>
            m = after_pat.match(line)
            if m:
                afterref = True
                verbatim = True
                    # Avoid an extra test in the main loop.
                continue
            #@-<< handle afterref >>
            #@+<< handle @first and @last >>
            #@+node:ekr.20180606053919.1: *4* << handle @first and @last >>
            m = first_pat.match(line)
            if m:
                if 0 <= first_i < len(first_lines):
                    body.append('@first ' + first_lines[first_i])
                    first_i += 1
                else:
                    g.trace('too many @first lines')
                continue
            m = last_pat.match(line)
            if m:
                n_last_lines += 1
                continue
            #@-<< handle @first and @last >>
            #@+<< handle @comment >>
            #@+node:ekr.20180621050901.1: *4* << handle @comment >>
            # http://leoeditor.com/directives.html#part-4-dangerous-directives
            m = comment_pat.match(line)
            if m:
                # <1, 2 or 3 comment delims>
                delims = m.group(1).strip()
                # Whatever happens, retain the @delims line.
                body.append('@comment %s\n' % delims)
                delim1, delim2, delim3 = g.set_delims_from_string(delims)
                    # delim1 is always the single-line delimiter.
                if delim1:
                    delim_start, delim_end = delim1, ''
                else:
                    delim_start, delim_end = delim2, delim3
                #
                # Within these delimiters:
                # - double underscores represent a newline.
                # - underscores represent a significant space,
                delim_start = delim_start.replace('__','\n').replace('_',' ')
                delim_end = delim_end.replace('__','\n').replace('_',' ')
                # Recalculate all delim-related values
                doc_skip = (delim_start + '\n', delim_end + '\n')
                is_cweb = delim_start == '@q@' and delim_end == '@>'
                sentinel = delim_start + '@'
                #
                # Recalculate the patterns.
                delims = delim_start, delim_end
                (
                    after_pat, all_pat, code_pat, comment_pat, delims_pat,
                    doc_pat, end_raw_pat, first_pat, last_pat,
                    node_start_pat, others_pat, raw_pat, ref_pat
                ) = self.get_patterns(delims)
                continue
            #@-<< handle @comment >>
            #@+<< handle @delims >>
            #@+node:ekr.20180608104836.1: *4* << handle @delims >>
            m = delims_pat.match(line)
            if m:
                # Get 1 or 2 comment delims
                # Whatever happens, retain the original @delims line.
                delims = m.group(1).strip()
                body.append('@delims %s\n' % delims)
                #
                # Parse the delims.
                delims_pat = re.compile(r'^([^ ]+)\s*([^ ]+)?')
                m2 = delims_pat.match(delims)
                if not m2:
                    g.trace('Ignoring invalid @comment: %r' % line)
                    continue
                delim_start = m2.group(1)
                delim_end = m2.group(2) or ''
                #
                # Within these delimiters:
                # - double underscores represent a newline.
                # - underscores represent a significant space,
                delim_start = delim_start.replace('__','\n').replace('_',' ')
                delim_end = delim_end.replace('__','\n').replace('_',' ')
                # Recalculate all delim-related values
                doc_skip = (delim_start + '\n', delim_end + '\n')
                is_cweb = delim_start == '@q@' and delim_end == '@>'
                sentinel = delim_start + '@'
                #
                # Recalculate the patterns
                delims = delim_start, delim_end
                (
                    after_pat, all_pat, code_pat, comment_pat, delims_pat,
                    doc_pat, end_raw_pat, first_pat, last_pat,
                    node_start_pat, others_pat, raw_pat, ref_pat
                ) = self.get_patterns(delims)
                continue
            #@-<< handle @delims >>
            #@+<< handle @raw >>
            #@+node:ekr.20180606080200.1: *4* << handle @raw >>
            # http://leoeditor.com/directives.html#part-4-dangerous-directives
            m = raw_pat.match(line)
            if m:
                in_raw = True
                verbatim = True
                    # Avoid an extra test in the main loop.
                continue
            #@-<< handle @raw >>
            #@+<< handle @-leo >>
            #@+node:ekr.20180602103135.20: *4* << handle @-leo >>
            if line.startswith(delim_start + '@-leo'):
                i += 1
                break
            #@-<< handle @-leo >>
            # These must be last, in this order.
            #@+<< Last 1. handle remaining @@ lines >>
            #@+node:ekr.20180603135602.1: *4* << Last 1. handle remaining @@ lines >>
            # @first, @last, @delims and @comment generate @@ sentinels,
            # So this must follow all of those.
            if line.startswith(delim_start + '@@'):
                ii = len(delim_start) + 1 # on second '@'
                jj = line.rfind(delim_end) if delim_end else -1
                body.append(line[ii:jj] + '\n')
                continue
            #@-<< Last 1. handle remaining @@ lines >>
            #@+<< Last 2. handle remaining @doc lines >>
            #@+node:ekr.20180606054325.1: *4* << Last 2. handle remaining @doc lines >>
            if in_doc:
                if delim_end:
                    # doc lines are unchanged.
                    body.append(line)
                else:
                    # Doc lines start with start_delim + one blank.
                    body.append(line[len(delim_start)+1:])
                continue
            #@-<< Last 2. handle remaining @doc lines >>
            #@+<< Last 3. handle remaining @ lines >>
            #@+node:ekr.20180602103135.17: *4* << Last 3. handle remaining @ lines >>
            # Probably can't happen: an apparent sentinel line.
            # Such lines should be @@ lines or follow @verbatim.
            #
            # This assert verifies the short-circuit test.
            assert strip_line.startswith(sentinel), (repr(sentinel), repr(line))
            #
            # This trace is less important, but interesting.
            g.trace('UNEXPECTED LINE:', repr(sentinel), repr(line), g.shortFileName(self.path))
            body.append(line)
            #@-<< Last 3. handle remaining @ lines >>
        else:
            # No @-leo sentinel
            return None, []
        # Handle @last lines.
        last_lines = lines[start+i:]
        if last_lines:
            last_lines = ['@last ' + z for z in last_lines]
            gnx2body[root_gnx] = gnx2body[root_gnx] + last_lines
        self.post_pass(gnx2body, gnx2vnode, root_v)
        return root_v, last_lines
    #@+node:ekr.20180603170614.1: *3* fast_at.read_into_root
    def read_into_root(self, contents, path, root):
        '''
        Parse the file's contents, creating a tree of vnodes
        anchored in root.v.
        '''
        trace = False
        t1 = time.clock()
        self.path = path
        self.root = root
        sfn = g.shortFileName(path)
        contents = contents.replace('\r','')
        lines = g.splitLines(contents)
        data = self.scan_header(lines)
        if data:
            # Clear all children.
            # Previously, this had been done in readOpenFile.
            root.v._deleteAllChildren()
            delims, first_lines, start_i = data
            self.scan_lines(
                delims, first_lines, lines, start_i)
            if trace:
                t2 = time.clock()
                g.trace('%5.3f sec. %s' % ((t2-t1), path))
            return True
        g.trace('Invalid external file: %s' % sfn)
        return False
    #@-others
#@-others
#@@language python
#@@tabwidth -4
#@@pagewidth 60
#@-leo
