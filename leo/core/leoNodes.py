#@+leo-ver=4-thin
#@+node:ekr.20031218072017.3320:@thin leoNodes.py
#@@language python
#@@tabwidth -4
#@@pagewidth 80

use_zodb = False

#@<< imports >>
#@+node:ekr.20060904165452.1:<< imports >>
if use_zodb:
    # It may be important to import ZODB first.
    try:
        import ZODB
        import ZODB.FileStorage
    except ImportError:
        ZODB = None
else:
    ZODB = None

import leo.core.leoGlobals as g

if g.app and g.app.use_psyco:
    # g.pr("enabled psyco classes",__file__)
    try: from psyco.classes import *
    except ImportError: pass

import time
import re
import itertools
#@nonl
#@-node:ekr.20060904165452.1:<< imports >>
#@nl

#@+others
#@+node:ekr.20031218072017.1991:class nodeIndices
# Indices are Python dicts containing 'id','loc','time' and 'n' keys.

class nodeIndices (object):

    """A class to implement global node indices (gnx's)."""

    #@    @+others
    #@+node:ekr.20031218072017.1992:nodeIndices.__init__
    def __init__ (self,id):

        """ctor for nodeIndices class"""

        self.userId = id
        self.defaultId = id

        # A Major simplification: Only assign the timestamp once.
        self.setTimeStamp()
        self.lastIndex = 0
    #@-node:ekr.20031218072017.1992:nodeIndices.__init__
    #@+node:ekr.20031218072017.1993:areEqual (no longer used)
    def areEqual (self,gnx1,gnx2):

        """Return True if all fields of gnx1 and gnx2 are equal"""

        # works whatever the format of gnx1 and gnx2.
        # This should never throw an exception.
        return gnx1 == gnx2
    #@-node:ekr.20031218072017.1993:areEqual (no longer used)
    #@+node:ekr.20031218072017.1994:get/setDefaultId
    # These are used by the fileCommands read/write code.

    def getDefaultId (self):

        """Return the id to be used by default in all gnx's"""
        return self.defaultId

    def setDefaultId (self,theId):

        """Set the id to be used by default in all gnx's"""
        self.defaultId = theId
    #@-node:ekr.20031218072017.1994:get/setDefaultId
    #@+node:ekr.20031218072017.1995:getNewIndex
    def getNewIndex (self):

        '''Create a new gnx.'''

        self.lastIndex += 1
        d = (self.userId,self.timeString,self.lastIndex)
        # g.trace(d)
        return d
    #@-node:ekr.20031218072017.1995:getNewIndex
    #@+node:ekr.20031218072017.1996:isGnx (not used)
    def isGnx (self,gnx):
        try:
            theId,t,n = gnx
            return t != None
        except Exception:
            return False
    #@-node:ekr.20031218072017.1996:isGnx (not used)
    #@+node:ekr.20031218072017.1997:scanGnx
    def scanGnx (self,s,i):

        """Create a gnx from its string representation"""

        if not g.isString(s):
            g.es("scanGnx: unexpected index type:",type(s),'',s,color="red")
            return None,None,None

        s = s.strip()

        theId,t,n = None,None,None
        i,theId = g.skip_to_char(s,i,'.')
        if g.match(s,i,'.'):
            i,t = g.skip_to_char(s,i+1,'.')
            if g.match(s,i,'.'):
                i,n = g.skip_to_char(s,i+1,'.')
        # Use self.defaultId for missing id entries.
        if theId == None or len(theId) == 0:
            theId = self.defaultId
        # Convert n to int.
        if n:
            try: n = int(n)
            except Exception: pass

        return theId,t,n
    #@-node:ekr.20031218072017.1997:scanGnx
    #@+node:ekr.20031218072017.1998:setTimeStamp
    def setTimestamp (self):

        """Set the timestamp string to be used by getNewIndex until further notice"""

        self.timeString = time.strftime(
            "%Y%m%d%H%M%S", # Help comparisons; avoid y2k problems.
            time.localtime())

        # g.trace(self.timeString,self.lastIndex,g.callers(4))

    setTimeStamp = setTimestamp
    #@-node:ekr.20031218072017.1998:setTimeStamp
    #@+node:ekr.20031218072017.1999:toString
    def toString (self,index):

        """Convert a gnx (a tuple) to its string representation"""

        try:
            theId,t,n = index
            if n in (None,0,'',):
                return "%s.%s" % (theId,t)
            else:
                return "%s.%s.%d" % (theId,t,n)
        except Exception:
            if not g.app.unitTesting:
                g.trace('unusual gnx',repr(index),g.callers()) 
            try:
                theId,t,n = self.getNewIndex()
                if n in (None,0,'',):
                    return "%s.%s" % (theId,t)
                else:
                    return "%s.%s.%d" % (theId,t,n)
            except Exception:
                g.trace('double exception: returning original index')
                return repr(index)
    #@nonl
    #@-node:ekr.20031218072017.1999:toString
    #@-others
#@-node:ekr.20031218072017.1991:class nodeIndices
#@+node:ekr.20031218072017.889:class position
#@<< about the position class >>
#@+node:ekr.20031218072017.890:<< about the position class >>
#@@killcolor
#@+at
# 
# A position marks the spot in a tree traversal. A position p consists of a 
# vnode
# p.v, a child index p._childIndex, and a stack of tuples (v,childIndex), one 
# for
# each ancestor **at the spot in tree traversal. Positions p has a unique set 
# of
# parents.
# 
# The p.moveToX methods may return a null (invalid) position p with p.v = 
# None.
# 
# The tests "if p" or "if not p" are the _only_ correct way to test whether a
# position p is valid. In particular, tests like "if p is None" or "if p is 
# not
# None" will not work properly.
#@-at
#@-node:ekr.20031218072017.890:<< about the position class >>
#@nl

# Positions should *never* be saved by the ZOBD.
class position (object):
    #@    @+others
    #@+node:ekr.20040228094013: p.ctor & other special methods...
    #@+node:ekr.20080416161551.190: p.__init__
    def __init__ (self,v,childIndex=0,stack=None,trace=False):

        '''Create a new position with the given childIndex and parent stack.'''

        # To support ZODB the code must set v._p_changed = 1
        # whenever any mutable vnode object changes.

        self._childIndex = childIndex
        self.v = v

        # New in Leo 4.5: stack entries are tuples (v,childIndex).
        if stack:
            self.stack = stack[:] # Creating a copy here is safest and best.
        else:
            self.stack = []

        g.app.positions += 1

        # if g.app.tracePositions and trace: g.trace(g.callers())

        self.txtOffset = None # see self.textOffset()
    #@-node:ekr.20080416161551.190: p.__init__
    #@+node:ekr.20080920052058.3:p.__eq__ & __ne__
    def __eq__(self,p2):

        """Return True if two postions are equivalent."""

        p1 = self

        # Don't use g.trace: it might call p.__eq__ or p.__ne__.
        # print ('p.__eq__: %s %s' % (
            # p1 and p1.v and p1.h,p2 and p2.v and p2.h))

        if p2 is None or p2.v is None:
            return p1.v is None
        else:
            return ( p1.v == p2.v and
                p1._childIndex == p2._childIndex and
                p1.stack == p2.stack )

    def __ne__(self,p2):

        """Return True if two postions are not equivalent."""

        return not self.__eq__(p2) # For possible use in Python 2.x.
    #@-node:ekr.20080920052058.3:p.__eq__ & __ne__
    #@+node:ekr.20091210082012.6230:p.__ge__ & __le__& __lt__
    def __ge__ (self,other):

        return self.__eq__(other) or self.__gt__(other)

    def __le__ (self,other):

        return self.__eq__(other) or self.__lt__(other)

    def __lt__ (self,other):

        return not self.__eq__(other) and not self.__gt__(other)
    #@-node:ekr.20091210082012.6230:p.__ge__ & __le__& __lt__
    #@+node:ekr.20091210082012.6233:p.__gt__
    def __gt__ (self,other):

        '''Return True if self appears after other in outline order.'''

        stack1,stack2 = self.stack,other.stack
        n1,n2 = len(stack1),len(stack2) ; n = min(n1,n2)
        # Compare the common part of the stacks.
        for item1,item2 in zip(stack1,stack2):
            v1,x1 = item1 ; v2,x2 = item2
            if x1 > x2: return True
            elif x1 < x2: return False
        # Finish the comparison.
        if n1 == n2:
            x1,x2 = self._childIndex,other._childIndex
            return x1 > x2
        elif n1 < n2:
            x1 = self._childIndex; v2,x2 = other.stack[n]
            return x1 > x2
        else:
            return True
    #@nonl
    #@-node:ekr.20091210082012.6233:p.__gt__
    #@+node:ekr.20040117170612:p.__getattr__ (no longer used)
    # No longer used.  All code must now be aware of the one-node world.

    # def __getattr__ (self,attr):

        # """Convert references to p.t into references to p.v."""

        # if attr=="t":
            # return self.v
        # else:
            # # New in 4.3: _silently_ raise the attribute error.
            # # This allows plugin code to use hasattr(p,attr) !
            # if 0:
                # print("unknown position attribute: %s" % attr)
                # import traceback ; traceback.print_stack()
            # raise AttributeError(attr)
    #@nonl
    #@-node:ekr.20040117170612:p.__getattr__ (no longer used)
    #@+node:ekr.20040117173448:p.__nonzero__ & __bool__
    #@+at
    # Tests such as 'if p' or 'if not p' are the _only_ correct ways to test 
    # whether a position p is valid.
    # In particular, tests like 'if p is None' or 'if p is not None' will not 
    # work properly.
    #@-at
    #@@c

    if g.isPython3:

        def __bool__ ( self):

            """Return True if a position is valid."""

            # Tracing this appears to cause unbounded prints.
            # print("__bool__",self.v and self.v.cleanHeadString())

            return self.v is not None

    else:

        def __nonzero__ ( self):

            """Return True if a position is valid."""

            # if g.app.trace: "__nonzero__",self.v

            # g.trace(repr(self))

            return self.v is not None
    #@-node:ekr.20040117173448:p.__nonzero__ & __bool__
    #@+node:ekr.20040301205720:p.__str__ and p.__repr__
    def __str__ (self):

        p = self

        if p.v:
            return "<pos %d childIndex: %d lvl: %d [%d] %s>" % (
                id(p),p._childIndex,p.level(),len(p.stack),p.cleanHeadString())
        else:
            return "<pos %d [%d] None>" % (id(p),len(p.stack))

    __repr__ = __str__
    #@-node:ekr.20040301205720:p.__str__ and p.__repr__
    #@+node:ekr.20061006092649:p.archivedPosition
    def archivedPosition (self,root_p=None):

        '''Return a representation of a position suitable for use in .leo files.'''

        p = self

        if root_p is None:
            aList = [z._childIndex for z in p.self_and_parents()]
        else:
            aList = []
            for z in p.self_and_parents():
                if z == root_p:
                    aList.append(0)
                    break
                else:
                    aList.append(z._childIndex)
            # g.trace(aList)

        aList.reverse()
        return aList
    #@nonl
    #@-node:ekr.20061006092649:p.archivedPosition
    #@+node:ekr.20040117171654:p.copy
    # Using this routine can generate huge numbers of temporary positions during a tree traversal.

    def copy (self):

        """"Return an independent copy of a position."""

        # if g.app.tracePositions: g.trace(g.callers())

        return position(self.v,self._childIndex,self.stack,trace=False)
    #@-node:ekr.20040117171654:p.copy
    #@+node:ekr.20040310153624:p.dump
    def dumpLink (self,link):

        return g.choose(link,link,"<none>")

    def dump (self,label=""):

        p = self
        if p.v:
            p.v.dump() # Don't print a label
    #@-node:ekr.20040310153624:p.dump
    #@+node:ekr.20080416161551.191:p.key
    def key (self):

        p = self

        # For unified nodes we must include a complete key,
        # so we can distinguish between clones.
        result = []
        for z in p.stack:
            v,childIndex = z
            result.append('%s:%s' % (id(v),childIndex))

        result.append('%s:%s' % (id(p.v),p._childIndex))

        return '.'.join(result)
    #@-node:ekr.20080416161551.191:p.key
    #@-node:ekr.20040228094013: p.ctor & other special methods...
    #@+node:ekr.20090128083459.74:p.Properties
    #@+node:ekr.20090128083459.75:p.b property
    def __get_b(self):

        p = self
        return p.bodyString()

    def __set_b(self,val):

        p = self ; c = p.v and p.v.context
        if c:
            c.setBodyString(p, val)
            # Don't redraw the screen: p.b must be fast.
            # c.redraw_after_icons_changed()

    b = property(
        __get_b, __set_b,
        doc = "position body string property")
    #@-node:ekr.20090128083459.75:p.b property
    #@+node:ekr.20090128083459.76:p.h property
    def __get_h(self):

        p = self
        return p.headString()

    def __set_h(self,val):

        p = self ; c = p.v and p.v.context
        if c:
            c.setHeadString(p,val)
            # Don't redraw the screen: p.h must be fast.
            # c.redraw_after_head_changed()

    h = property(
        __get_h, __set_h,
        doc = "position headline string property")  
    #@-node:ekr.20090128083459.76:p.h property
    #@+node:ekr.20090215165030.3:p.gnx property
    def __get_gnx(self):
        p = self
        return g.app.nodeIndices.toString(p.v.fileIndex)

    gnx = property(
        __get_gnx, # __set_gnx,
        doc = "position gnx property")
    #@-node:ekr.20090215165030.3:p.gnx property
    #@-node:ekr.20090128083459.74:p.Properties
    #@+node:ekr.20040306212636:p.Getters
    #@+node:ekr.20040306210951:p.vnode proxies
    #@+node:ekr.20040306211032:p.Comparisons
    def anyAtFileNodeName         (self): return self.v.anyAtFileNodeName()
    def atAutoNodeName            (self): return self.v.atAutoNodeName()
    def atEditNodeName            (self): return self.v.atEditNodeName()
    def atFileNodeName            (self): return self.v.atFileNodeName()
    def atNoSentinelsFileNodeName (self): return self.v.atNoSentinelsFileNodeName()
    # def atRawFileNodeName         (self): return self.v.atRawFileNodeName()
    def atShadowFileNodeName      (self): return self.v.atShadowFileNodeName()
    def atSilentFileNodeName      (self): return self.v.atSilentFileNodeName()
    def atThinFileNodeName        (self): return self.v.atThinFileNodeName()

    # New names, less confusing
    atNoSentFileNodeName  = atNoSentinelsFileNodeName
    atAsisFileNodeName    = atSilentFileNodeName

    def isAnyAtFileNode         (self): return self.v.isAnyAtFileNode()
    def isAtAllNode             (self): return self.v.isAtAllNode()
    def isAtAutoNode            (self): return self.v.isAtAutoNode()
    def isAtAutoRstNode         (self): return self.v.isAtAutoRstNode()
    def isAtEditNode            (self): return self.v.isAtEditNode()
    def isAtFileNode            (self): return self.v.isAtFileNode()
    def isAtIgnoreNode          (self): return self.v.isAtIgnoreNode()
    def isAtNoSentinelsFileNode (self): return self.v.isAtNoSentinelsFileNode()
    def isAtOthersNode          (self): return self.v.isAtOthersNode()
    # def isAtRawFileNode         (self): return self.v.isAtRawFileNode()
    def isAtSilentFileNode      (self): return self.v.isAtSilentFileNode()
    def isAtShadowFileNode      (self): return self.v.isAtShadowFileNode()
    def isAtThinFileNode        (self): return self.v.isAtThinFileNode()

    # New names, less confusing:
    isAtNoSentFileNode = isAtNoSentinelsFileNode
    isAtAsisFileNode   = isAtSilentFileNode

    # Utilities.
    def matchHeadline (self,pattern): return self.v.matchHeadline(pattern)
    #@-node:ekr.20040306211032:p.Comparisons
    #@+node:ekr.20040306220230:p.Headline & body strings
    def bodyString (self):

        return self.v.bodyString()

    def headString (self):

        return self.v.headString()

    def cleanHeadString (self):

        return self.v.cleanHeadString()
    #@-node:ekr.20040306220230:p.Headline & body strings
    #@+node:ekr.20040306214401:p.Status bits
    def isDirty     (self): return self.v.isDirty()
    def isExpanded  (self): return self.v.isExpanded()
    def isMarked    (self): return self.v.isMarked()
    def isOrphan    (self): return self.v.isOrphan()
    def isSelected  (self): return self.v.isSelected()
    def isTopBitSet (self): return self.v.isTopBitSet()
    def isVisited   (self): return self.v.isVisited()
    def status      (self): return self.v.status()
    #@-node:ekr.20040306214401:p.Status bits
    #@-node:ekr.20040306210951:p.vnode proxies
    #@+node:ekr.20040306214240.2:p.children & parents
    #@+node:ekr.20040326064330:p.childIndex
    # This used to be time-critical code.

    def childIndex(self):

        p = self
        return p._childIndex
    #@-node:ekr.20040326064330:p.childIndex
    #@+node:ekr.20040323160302:p.directParents
    def directParents (self):

        return self.v.directParents()
    #@-node:ekr.20040323160302:p.directParents
    #@+node:ekr.20040306214240.3:p.hasChildren & p.numberOfChildren
    def hasChildren (self):

        p = self
        return len(p.v.children) > 0

    hasFirstChild = hasChildren

    def numberOfChildren (self):

        p = self
        return len(p.v.children)
    #@-node:ekr.20040306214240.3:p.hasChildren & p.numberOfChildren
    #@-node:ekr.20040306214240.2:p.children & parents
    #@+node:ekr.20031218072017.915:p.getX & vnode compatibility traversal routines
    # These methods are useful abbreviations.
    # Warning: they make copies of positions, so they should be used _sparingly_

    def getBack          (self): return self.copy().moveToBack()
    def getFirstChild    (self): return self.copy().moveToFirstChild()
    def getLastChild     (self): return self.copy().moveToLastChild()
    def getLastNode      (self): return self.copy().moveToLastNode()
    # def getLastVisible   (self): return self.copy().moveToLastVisible()
    def getNext          (self): return self.copy().moveToNext()
    def getNodeAfterTree (self): return self.copy().moveToNodeAfterTree()
    def getNthChild    (self,n): return self.copy().moveToNthChild(n)
    def getParent        (self): return self.copy().moveToParent()
    def getThreadBack    (self): return self.copy().moveToThreadBack()
    def getThreadNext    (self): return self.copy().moveToThreadNext()

    # New in Leo 4.4.3 b2: add c args.
    def getVisBack (self,c): return self.copy().moveToVisBack(c)
    def getVisNext (self,c): return self.copy().moveToVisNext(c)

    # These are efficient enough now that iterators are the normal way to traverse the tree!

    back          = getBack
    firstChild    = getFirstChild
    lastChild     = getLastChild
    lastNode      = getLastNode
    # lastVisible   = getLastVisible # New in 4.2 (was in tk tree code).
    next          = getNext
    nodeAfterTree = getNodeAfterTree
    nthChild      = getNthChild
    parent        = getParent
    threadBack    = getThreadBack
    threadNext    = getThreadNext
    visBack       = getVisBack
    visNext       = getVisNext

    # New in Leo 4.4.3:
    hasVisBack = visBack
    hasVisNext = visNext
    #@nonl
    #@-node:ekr.20031218072017.915:p.getX & vnode compatibility traversal routines
    #@+node:ekr.20080416161551.192:p.hasX
    def hasBack(self):
        p = self
        return p.v and p._childIndex > 0

    def hasNext(self):
        p = self
        try:
            parent_v = p._parentVnode()
                # Returns None if p.v is None.
            return p.v and parent_v and p._childIndex+1 < len(parent_v.children)
        except Exception:
            g.trace('*** Unexpected exception')
            g.es_exception()
            return None

    def hasParent(self):
        p = self
        return p.v and len(p.stack) > 0

    def hasThreadBack(self):
        p = self
        return p.hasParent() or p.hasBack() # Much cheaper than computing the actual value.
    #@+node:ekr.20080416161551.193:hasThreadNext (the only complex hasX method)
    def hasThreadNext (self):

        p = self
        if not p.v: return False

        if p.hasChildren() or p.hasNext(): return True

        n = len(p.stack) -1
        while n >= 0:
            v,childIndex = p.stack[n]
            # See how many children v's parent has.
            if n == 0:
                parent_v = v.context.hiddenRootNode
            else:
                parent_v,junk = p.stack[n-1]
            if len(parent_v.children) > childIndex+1:
                # v has a next sibling.
                return True
            n -= 1
        return False
    #@-node:ekr.20080416161551.193:hasThreadNext (the only complex hasX method)
    #@-node:ekr.20080416161551.192:p.hasX
    #@+node:ekr.20060920203352:p.findRootPosition
    def findRootPosition (self):

        p = self.copy()
        while p.hasParent():
            p.moveToParent()
        while p.hasBack():
            p.moveToBack()
        return p
    #@nonl
    #@-node:ekr.20060920203352:p.findRootPosition
    #@+node:ekr.20080416161551.194:p.isAncestorOf
    def isAncestorOf (self, p2):

        p = self ; v = p.v

        for z in p2.stack:
            v2,junk = z
            if v2 == v:
                return True

        return False
    #@-node:ekr.20080416161551.194:p.isAncestorOf
    #@+node:ekr.20040306215056:p.isCloned
    def isCloned (self):

        p = self
        return p.v.isCloned()
    #@-node:ekr.20040306215056:p.isCloned
    #@+node:ekr.20040307104131.2:p.isRoot
    def isRoot (self):

        p = self

        return not p.hasParent() and not p.hasBack()
    #@-node:ekr.20040307104131.2:p.isRoot
    #@+node:ekr.20080416161551.196:p.isVisible
    def isVisible (self,c):

        p = self ; trace = False
        limit,limitIsVisible = c.visLimit()
        limit_v = limit and limit.v or None
        if p.v == limit_v:
            if trace: g.trace('*** at limit','limitIsVisible',limitIsVisible,p.h)
            return limitIsVisible

        # It's much easier with a full stack.
        n = len(p.stack)-1
        while n >= 0:
            progress = n
            # v,n = p.vParentWithStack(v,p.stack,n)
            v,junk = p.stack[n]
            if v == limit_v:  # We are at a descendant of limit.
                if trace: g.trace('*** descendant of limit',
                    'limitIsVisible',limitIsVisible,
                    'limit.isExpanded()',limit.isExpanded(),'v',v)
                if limitIsVisible:
                    return limit.isExpanded()
                else: # Ignore the expansion state of @chapter nodes.
                    return True
            if not v.isExpanded():
                if trace: g.trace('*** non-limit parent is not expanded:',v._headString,p.h)
                return False
            n -= 1
            assert progress > n

        return True
    #@-node:ekr.20080416161551.196:p.isVisible
    #@+node:ekr.20080416161551.197:p.level & simpleLevel
    def level (self):

        '''Return the number of p's parents.'''

        p = self
        return p.v and len(p.stack) or 0

    simpleLevel = level
    #@-node:ekr.20080416161551.197:p.level & simpleLevel
    #@+node:shadow.20080825171547.2:p.textOffset
    def textOffset(self):
        '''
            See http://tinyurl.com/5nescw for details
        '''

        p = self

        # caching of p.textOffset, we need to calculate it only once
        if p.txtOffset is not None:
            return p.txtOffset

        p.txtOffset = 0
        # walk back from the current position
        for cursor in p.self_and_parents():
            # we also need the parent, the "text offset" is relative to it
            parent = cursor.parent()
            if parent == None: # root reached
                break
            parent_bodyString = parent.b
            if parent_bodyString == '': # organizer node
                continue
            parent_lines = parent_bodyString.split('\n')
            # check out if the cursor node is a section
            cursor_is_section = False
            cursor_headString = cursor.h
            if cursor_headString.startswith('<<'):
                cursor_is_section = True # section node
            for line in parent_lines:
                if cursor_is_section == True:
                    # find out the section in the bodyString of the parent
                    pos = line.find(cursor_headString)
                else:
                    # otherwise find the "@others" directive in the bodyString of the parent
                    pos = line.find('@others')
                if pos > 0:
                    # break the iteration over lines if something is found 
                    break
            if pos > 0:
                p.txtOffset += pos
            if parent.v.isAnyAtFileNode(): # do not scan upper
                break

        return p.txtOffset         
    #@-node:shadow.20080825171547.2:p.textOffset
    #@-node:ekr.20040306212636:p.Getters
    #@+node:ekr.20040305222924:p.Setters
    #@+node:ekr.20040306220634:p.Vnode proxies
    #@+node:ekr.20040306220634.9:p.Status bits
    # Clone bits are no longer used.
    # Dirty bits are handled carefully by the position class.

    def clearMarked  (self): return self.v.clearMarked()
    def clearOrphan  (self): return self.v.clearOrphan()
    def clearVisited (self): return self.v.clearVisited()

    def contract (self): return self.v.contract()
    def expand   (self): return self.v.expand()

    def initExpandedBit    (self): return self.v.initExpandedBit()
    def initMarkedBit      (self): return self.v.initMarkedBit()
    def initStatus (self, status): return self.v.initStatus(status)

    def setMarked   (self): return self.v.setMarked()
    def setOrphan   (self): return self.v.setOrphan()
    def setSelected (self): return self.v.setSelected()
    def setVisited  (self): return self.v.setVisited()
    #@-node:ekr.20040306220634.9:p.Status bits
    #@+node:ekr.20040306220634.8:p.computeIcon & p.setIcon
    def computeIcon (self):

        return self.v.computeIcon()

    def setIcon (self):

        pass # Compatibility routine for old scripts
    #@-node:ekr.20040306220634.8:p.computeIcon & p.setIcon
    #@+node:ekr.20040306220634.29:p.setSelection
    def setSelection (self,start,length):

        return self.v.setSelection(start,length)
    #@-node:ekr.20040306220634.29:p.setSelection
    #@-node:ekr.20040306220634:p.Vnode proxies
    #@+node:ekr.20040315034158:p.setBodyString & setHeadString
    def setBodyString (self,s):

        p = self
        return p.v.setBodyString(s)

    initBodyString = setBodyString
    setTnodeText = setBodyString
    scriptSetBodyString = setBodyString

    def initHeadString (self,s):

        p = self
        p.v.initHeadString(s)

    def setHeadString (self,s):

        p = self
        p.v.initHeadString(s)
        # Note: p.setDirty is expensive.
        # We can't change this because Leo's core uses
        # p.setDirty and c.setDirty interchangeably.
        p.setDirty()
    #@nonl
    #@-node:ekr.20040315034158:p.setBodyString & setHeadString
    #@+node:ekr.20040312015908:p.Visited bits
    #@+node:ekr.20040306220634.17:p.clearVisitedInTree
    # Compatibility routine for scripts.

    def clearVisitedInTree (self):

        for p in self.self_and_subtree():
            p.clearVisited()
    #@-node:ekr.20040306220634.17:p.clearVisitedInTree
    #@+node:ekr.20031218072017.3388:p.clearAllVisitedInTree
    def clearAllVisitedInTree (self):

        for p in self.self_and_subtree():
            p.v.clearVisited()
            p.v.clearWriteBit()
    #@-node:ekr.20031218072017.3388:p.clearAllVisitedInTree
    #@-node:ekr.20040312015908:p.Visited bits
    #@+node:ekr.20040305162628:p.Dirty bits
    #@+node:ekr.20040311113514:p.clearDirty
    def clearDirty (self):

        p = self
        p.v.clearDirty()
    #@-node:ekr.20040311113514:p.clearDirty
    #@+node:ekr.20040318125934:p.findAllPotentiallyDirtyNodes
    def findAllPotentiallyDirtyNodes(self):

        p = self
        return p.v.findAllPotentiallyDirtyNodes()
    #@-node:ekr.20040318125934:p.findAllPotentiallyDirtyNodes
    #@+node:ekr.20040702104823:p.inAtIgnoreRange
    def inAtIgnoreRange (self):

        """Returns True if position p or one of p's parents is an @ignore node."""

        p = self

        for p in p.self_and_parents():
            if p.isAtIgnoreNode():
                return True

        return False
    #@-node:ekr.20040702104823:p.inAtIgnoreRange
    #@+node:ekr.20040303214038:p.setAllAncestorAtFileNodesDirty
    def setAllAncestorAtFileNodesDirty (self,setDescendentsDirty=False):

        trace = False and not g.unitTesting
        verbose = False
        p = self
        dirtyVnodeList = []

        # Calculate all nodes that are joined to p or parents of such nodes.
        nodes = p.findAllPotentiallyDirtyNodes()

        if setDescendentsDirty:
            # N.B. Only mark _direct_ descendents of nodes.
            # Using the findAllPotentiallyDirtyNodes algorithm would mark way too many nodes.
            for p2 in p.subtree():
                # Only @thin nodes need to be marked.
                if p2.v not in nodes and p2.isAtThinFileNode():
                    nodes.append(p2.v)

        if trace and verbose:
            for v in nodes:
                print (v.isDirty(),v.isAnyAtFileNode(),v)

        dirtyVnodeList = [v for v in nodes
            if not v.isDirty() and v.isAnyAtFileNode()]
        changed = len(dirtyVnodeList) > 0

        for v in dirtyVnodeList:
            v.setDirty()

        if trace: g.trace("position",dirtyVnodeList,g.callers(5))

        return dirtyVnodeList
    #@-node:ekr.20040303214038:p.setAllAncestorAtFileNodesDirty
    #@+node:ekr.20040303163330:p.setDirty
    def setDirty (self,setDescendentsDirty=True):

        '''Mark a node and all ancestor @file nodes dirty.'''

        p = self ; dirtyVnodeList = []

        # g.trace(p.h,g.callers(4))

        if not p.v.isDirty():
            p.v.setDirty()
            dirtyVnodeList.append(p.v)

        # Important: this must be called even if p.v is already dirty.
        # Typing can change the @ignore state!
        dirtyVnodeList2 = p.setAllAncestorAtFileNodesDirty(setDescendentsDirty)
        dirtyVnodeList.extend(dirtyVnodeList2)

        return dirtyVnodeList
    #@-node:ekr.20040303163330:p.setDirty
    #@-node:ekr.20040305162628:p.Dirty bits
    #@-node:ekr.20040305222924:p.Setters
    #@+node:ekr.20040315023430:p.File Conversion
    #@+at
    # - convertTreeToString and moreHead can't be vnode methods because they 
    # uses level().
    # - moreBody could be anywhere: it may as well be a postion method.
    #@-at
    #@+node:ekr.20040315023430.1:p.convertTreeToString
    def convertTreeToString (self):

        """Convert a positions  suboutline to a string in MORE format."""

        p = self ; level1 = p.level()

        array = []
        for p in p.self_and_subtree():
            array.append(p.moreHead(level1)+'\n')
            body = p.moreBody()
            if body:
                array.append(body +'\n')

        return ''.join(array)
    #@-node:ekr.20040315023430.1:p.convertTreeToString
    #@+node:ekr.20040315023430.2:p.moreHead
    def moreHead (self, firstLevel,useVerticalBar=False):

        """Return the headline string in MORE format."""

        # useVerticalBar is unused, but it would be useful in over-ridden methods.

        p = self
        level = self.level() - firstLevel
        plusMinus = g.choose(p.hasChildren(), "+", "-")

        return "%s%s %s" % ('\t'*level,plusMinus,p.h)
    #@-node:ekr.20040315023430.2:p.moreHead
    #@+node:ekr.20040315023430.3:p.moreBody
    #@+at 
    #     + test line
    #     - test line
    #     \ test line
    #     test line +
    #     test line -
    #     test line \
    #     More lines...
    #@-at
    #@@c

    def moreBody (self):

        """Returns the body string in MORE format.  

        Inserts a backslash before any leading plus, minus or backslash."""

        p = self ; array = []
        lines = p.b.split('\n')
        for s in lines:
            i = g.skip_ws(s,0)
            if i < len(s) and s[i] in ('+','-','\\'):
                s = s[:i] + '\\' + s[i:]
            array.append(s)
        return '\n'.join(array)
    #@-node:ekr.20040315023430.3:p.moreBody
    #@-node:ekr.20040315023430:p.File Conversion
    #@+node:ekr.20091001141621.6060:p.generators
    #@+node:ekr.20091001141621.6055:p.children
    def children(self):

        '''Return all children of p.'''

        p = self
        p = p.firstChild()
        while p:
            yield p
            p.moveToNext()
        raise StopIteration

    # Compatibility with old code.
    children_iter = children
    #@-node:ekr.20091001141621.6055:p.children
    #@+node:ekr.20091002083910.6102:p.following_siblings
    def following_siblings(self):
        '''
        Return all siblings that follow p, not including p.
        '''

        p = self
        p = p.copy() # Always include the original node.
        p = p.next()
        while p:
            yield p
            p.moveToNext()
        raise StopIteration

    # Compatibility with old code.
    following_siblings_iter = following_siblings
    #@-node:ekr.20091002083910.6102:p.following_siblings
    #@+node:ekr.20091002083910.6104:p.nodes
    def nodes (self):

        p = self
        p = p.copy()
        while p:
            yield p.v
            p.moveToThreadNext()

    # Compatibility with old code.
    tnodes_iter = nodes
    vnodes_iter = nodes
    #@-node:ekr.20091002083910.6104:p.nodes
    #@+node:ekr.20091001141621.6058:p.parents
    def parents(self):

        '''Return all parents of p.'''

        p = self
        p = p.parent()
        while p:
            yield p
            p.moveToParent()
        raise StopIteration

    # Compatibility with old code.
    parents_iter = parents
    #@-node:ekr.20091001141621.6058:p.parents
    #@+node:ekr.20091002083910.6099:p.self_and_parents
    def self_and_parents(self):

        '''Return p and all parents of p.'''

        p = self
        p = p.copy()
        while p:
            yield p
            p.moveToParent()
        raise StopIteration

    # Compatibility with old code.
    self_and_parents_iter = self_and_parents
    #@-node:ekr.20091002083910.6099:p.self_and_parents
    #@+node:ekr.20091001141621.6057:p.self_and_siblings
    def self_and_siblings(self):
        '''Return all siblings of p including p.
        '''

        p = self
        p = p.copy()
        while p.hasBack():
            p.moveToBack()
        while p:
            yield p
            p.moveToNext()
        raise StopIteration

    # Compatibility with old code.
    self_and_siblings_iter = self_and_siblings
    #@nonl
    #@-node:ekr.20091001141621.6057:p.self_and_siblings
    #@+node:ekr.20091001141621.6066:p.self_and_subtree
    def self_and_subtree(self):

        '''Return p's entire subtree, including p.'''

        p = self
        p = p.copy()
        after = p.nodeAfterTree()
        while p and p != after:
            yield p
            p.moveToThreadNext()
        raise StopIteration

    # Compatibility with old code.
    self_and_subtree_iter = self_and_subtree
    #@-node:ekr.20091001141621.6066:p.self_and_subtree
    #@+node:ekr.20091001141621.6056:p.subtree
    def subtree(self):

        '''Return all descendants of p, not including p.'''

        p = self
        p = p.copy()
        after = p.nodeAfterTree()
        p.moveToThreadNext()
        while p and p != after:
            yield p
            p.moveToThreadNext()
        raise StopIteration

    # Compatibility with old code.
    subtree_iter = subtree
    #@-node:ekr.20091001141621.6056:p.subtree
    #@+node:ekr.20091002083910.6105:p.unique_nodes
    def unique_nodes (self):

        p = self
        p = p.copy()
        seen = set()
        while p:
            if p.v in seen:
                p.moveToNodeAfterTree()
            else:
                seen.add(p.v)
                yield p.v
                p.moveToThreadNext()

    # Compatibility with old code.
    unique_tnodes_iter = unique_nodes
    unique_vnodes_iter = unique_nodes
    #@-node:ekr.20091002083910.6105:p.unique_nodes
    #@+node:ekr.20091002083910.6103:p.unique_subtree
    def unique_subtree (self):
        '''Return unique positions in p's entire subtree, including p.'''

        p = self
        p = p.copy()
        after = p.nodeAfterTree()
        seen = set()
        while p and p != after:
            if p.v in seen:
                p.moveToNodeAfterTree()
            else:
                seen.add(p.v)
                yield p
                p.moveToThreadNext()
        raise StopIteration

    # Compatibility with old code.
    subtree_with_unique_tnodes_iter = unique_subtree
    subtree_with_unique_vnodes_iter = unique_subtree
    #@-node:ekr.20091002083910.6103:p.unique_subtree
    #@-node:ekr.20091001141621.6060:p.generators
    #@+node:ekr.20040303175026:p.Moving, Inserting, Deleting, Cloning, Sorting
    #@+node:ekr.20040303175026.8:p.clone
    def clone (self):

        """Create a clone of back.

        Returns the newly created position."""

        p = self
        p2 = p.copy() # Do *not* copy the vnode!
        p2._linkAfter(p) # This should "just work"
        return p2
    #@-node:ekr.20040303175026.8:p.clone
    #@+node:ekr.20040303175026.9:p.copyTreeAfter, copyTreeTo
    # These used by unit tests and by the group_operations plugin.

    def copyTreeAfter(self):
        p = self
        p2 = p.insertAfter()
        p.copyTreeFromSelfTo(p2)
        return p2

    def copyTreeFromSelfTo(self,p2):
        p = self
        p2.v._headString = p.h
        p2.v._bodyString = p.b

        # 2009/10/02: no need to copy arg to iter
        for child in p.children():
            child2 = p2.insertAsLastChild()
            child.copyTreeFromSelfTo(child2)
    #@-node:ekr.20040303175026.9:p.copyTreeAfter, copyTreeTo
    #@+node:ekr.20040303175026.2:p.doDelete
    #@+at 
    #@nonl
    # This is the main delete routine.
    # It deletes the receiver's entire tree from the screen.
    # Because of the undo command we never actually delete vnodes or tnodes.
    #@-at
    #@@c

    def doDelete (self,newNode=None):

        """Deletes position p from the outline."""

        p = self
        p.setDirty() # Mark @file nodes dirty!

        # Adjust newNode._childIndex if newNode is a following sibling of p.
        sib = p.copy()
        while sib.hasNext():
            sib.moveToNext()
            if sib == newNode:
                newNode._childIndex -= 1
                break

        p._unlink()
    #@-node:ekr.20040303175026.2:p.doDelete
    #@+node:ekr.20040303175026.3:p.insertAfter
    def insertAfter (self):

        """Inserts a new position after self.

        Returns the newly created position."""

        p = self ; context = p.v.context
        p2 = self.copy()

        p2.v = vnode(context=context)
        p2.v.iconVal = 0
        p2._linkAfter(p)

        return p2
    #@-node:ekr.20040303175026.3:p.insertAfter
    #@+node:ekr.20040303175026.4:p.insertAsLastChild
    def insertAsLastChild (self):

        """Inserts a new vnode as the last child of self.

        Returns the newly created position."""

        p = self
        n = p.numberOfChildren()

        return p.insertAsNthChild(n)
    #@-node:ekr.20040303175026.4:p.insertAsLastChild
    #@+node:ekr.20040303175026.5:p.insertAsNthChild
    def insertAsNthChild (self,n):

        """Inserts a new node as the the nth child of self.
        self must have at least n-1 children.

        Returns the newly created position."""

        p = self ; context = p.v.context
        p2 = self.copy()

        p2.v = vnode(context=context)
        p2.v.iconVal = 0
        p2._linkAsNthChild(p,n)

        return p2
    #@-node:ekr.20040303175026.5:p.insertAsNthChild
    #@+node:ekr.20040310062332.1:p.invalidOutline
    def invalidOutline (self, message):

        p = self

        if p.hasParent():
            node = p.parent()
        else:
            node = p

        g.alert("invalid outline: %s\n%s" % (message,node))
    #@-node:ekr.20040310062332.1:p.invalidOutline
    #@+node:ekr.20040303175026.10:p.moveAfter
    def moveAfter (self,a):

        """Move a position after position a."""

        p = self # Do NOT copy the position!

        # g.trace('before','p',p,p.stack,'\na',a,a.stack)

        a._adjustPositionBeforeUnlink(p)
        p._unlink()
        p._linkAfter(a)

        # g.trace('before','p',p,p.stack,'\na',a,a.stack)

        return p
    #@-node:ekr.20040303175026.10:p.moveAfter
    #@+node:ekr.20040306060312:p.moveToFirst/LastChildOf
    def moveToFirstChildOf (self,parent):

        """Move a position to the first child of parent."""

        p = self # Do NOT copy the position!
        p._unlink()
        p._linkAsNthChild(parent,0)
        return p


    def moveToLastChildOf (self,parent):

        """Move a position to the last child of parent."""

        p = self # Do NOT copy the position!
        p._unlink()
        n = parent.numberOfChildren()
        p._linkAsNthChild(parent,n)
        return p
    #@-node:ekr.20040306060312:p.moveToFirst/LastChildOf
    #@+node:ekr.20040303175026.11:p.moveToNthChildOf
    def moveToNthChildOf (self,parent,n):

        """Move a position to the nth child of parent."""

        p = self # Do NOT copy the position!

        parent._adjustPositionBeforeUnlink(p)
        p._unlink()
        p._linkAsNthChild(parent,n)

        return p
    #@-node:ekr.20040303175026.11:p.moveToNthChildOf
    #@+node:ekr.20040303175026.6:p.moveToRoot
    def moveToRoot (self,oldRoot=None):

        '''Moves a position to the root position.

        Important: oldRoot must the previous root position if it exists.'''

        p = self # Do NOT copy the position!
        if oldRoot:
            oldRoot._adjustPositionBeforeUnlink(p)
        p._unlink()
        p._linkAsRoot(oldRoot)

        return p
    #@-node:ekr.20040303175026.6:p.moveToRoot
    #@+node:ekr.20040303175026.13:p.validateOutlineWithParent
    # This routine checks the structure of the receiver's tree.

    def validateOutlineWithParent (self,pv):

        p = self
        result = True # optimists get only unpleasant surprises.
        parent = p.getParent()
        childIndex = p._childIndex

        # g.trace(p,parent,pv)
        #@    << validate parent ivar >>
        #@+node:ekr.20040303175026.14:<< validate parent ivar >>
        if parent != pv:
            p.invalidOutline( "Invalid parent link: " + repr(parent))
        #@-node:ekr.20040303175026.14:<< validate parent ivar >>
        #@nl
        #@    << validate childIndex ivar >>
        #@+node:ekr.20040303175026.15:<< validate childIndex ivar >>
        if pv:
            if childIndex < 0:
                p.invalidOutline ( "missing childIndex" + childIndex )
            elif childIndex >= pv.numberOfChildren():
                p.invalidOutline ( "missing children entry for index: " + childIndex )
        elif childIndex < 0:
            p.invalidOutline ( "negative childIndex" + childIndex )
        #@-node:ekr.20040303175026.15:<< validate childIndex ivar >>
        #@nl
        #@    << validate x ivar >>
        #@+node:ekr.20040303175026.16:<< validate x ivar >>
        if not p.v and pv:
            self.invalidOutline ( "Empty t" )
        #@-node:ekr.20040303175026.16:<< validate x ivar >>
        #@nl

        # Recursively validate all the children.
        for child in p.children():
            r = child.validateOutlineWithParent(p)
            if not r: result = False

        return result
    #@-node:ekr.20040303175026.13:p.validateOutlineWithParent
    #@-node:ekr.20040303175026:p.Moving, Inserting, Deleting, Cloning, Sorting
    #@+node:ekr.20080416161551.199:p.moveToX
    #@+at
    # These routines change self to a new position "in place".
    # That is, these methods must _never_ call p.copy().
    # 
    # When moving to a nonexistent position, these routines simply set p.v = 
    # None,
    # leaving the p.stack unchanged. This allows the caller to "undo" the 
    # effect of
    # the invalid move by simply restoring the previous value of p.v.
    # 
    # These routines all return self on exit so the following kind of code 
    # will work:
    #     after = p.copy().moveToNodeAfterTree()
    #@-at
    #@+node:ekr.20080416161551.200:p.moveToBack
    def moveToBack (self):

        """Move self to its previous sibling."""

        p = self ; n = p._childIndex

        parent_v = p._parentVnode()
            # Returns None if p.v is None.

        # Do not assume n is in range: this is used by positionExists.
        if parent_v and p.v and 0 < n <= len(parent_v.children):
            p._childIndex -= 1
            p.v = parent_v.children[n-1]
        else:
            p.v = None

        return p
    #@-node:ekr.20080416161551.200:p.moveToBack
    #@+node:ekr.20080416161551.201:p.moveToFirstChild
    def moveToFirstChild (self):

        """Move a position to it's first child's position."""

        p = self

        if p.v and p.v.children:
            p.stack.append((p.v,p._childIndex),)
            p.v = p.v.children[0]
            p._childIndex = 0
        else:
            p.v = None

        return p
    #@nonl
    #@-node:ekr.20080416161551.201:p.moveToFirstChild
    #@+node:ekr.20080416161551.202:p.moveToLastChild
    def moveToLastChild (self):

        """Move a position to it's last child's position."""

        p = self

        if p.v and p.v.children:
            p.stack.append((p.v,p._childIndex),)
            n = len(p.v.children)
            p.v = p.v.children[n-1]
            p._childIndex = n-1
        else:
            p.v = None

        return p
    #@-node:ekr.20080416161551.202:p.moveToLastChild
    #@+node:ekr.20080416161551.203:p.moveToLastNode
    def moveToLastNode (self):

        """Move a position to last node of its tree.

        N.B. Returns p if p has no children."""

        p = self

        # Huge improvement for 4.2.
        while p.hasChildren():
            p.moveToLastChild()

        return p
    #@-node:ekr.20080416161551.203:p.moveToLastNode
    #@+node:ekr.20080416161551.204:p.moveToNext
    def moveToNext (self):

        """Move a position to its next sibling."""

        p = self ; n = p._childIndex

        parent_v = p._parentVnode()
            # Returns None if p.v is None.
        if not p.v: g.trace('parent_v',parent_v,'p.v',p.v)

        if p.v and parent_v and len(parent_v.children) > n+1:
            p._childIndex = n+1
            p.v = parent_v.children[n+1]
        else:
            p.v = None

        return p
    #@-node:ekr.20080416161551.204:p.moveToNext
    #@+node:ekr.20080416161551.205:p.moveToNodeAfterTree
    def moveToNodeAfterTree (self):

        """Move a position to the node after the position's tree."""

        p = self

        while p:
            if p.hasNext():
                p.moveToNext()
                break
            p.moveToParent()

        return p
    #@-node:ekr.20080416161551.205:p.moveToNodeAfterTree
    #@+node:ekr.20080416161551.206:p.moveToNthChild
    def moveToNthChild (self,n):

        p = self

        if p.v and len(p.v.children) > n:
            p.stack.append((p.v,p._childIndex),)
            p.v = p.v.children[n]
            p._childIndex = n
        else:
            p.v = None

        return p
    #@-node:ekr.20080416161551.206:p.moveToNthChild
    #@+node:ekr.20080416161551.207:p.moveToParent
    def moveToParent (self):

        """Move a position to its parent position."""

        p = self

        if p.v and p.stack:
            p.v,p._childIndex = p.stack.pop()
        else:
            p.v = None

        return p
    #@-node:ekr.20080416161551.207:p.moveToParent
    #@+node:ekr.20080416161551.208:p.moveToThreadBack
    def moveToThreadBack (self):

        """Move a position to it's threadBack position."""

        p = self

        if p.hasBack():
            p.moveToBack()
            p.moveToLastNode()
        else:
            p.moveToParent()

        return p
    #@-node:ekr.20080416161551.208:p.moveToThreadBack
    #@+node:ekr.20080416161551.209:p.moveToThreadNext
    def moveToThreadNext (self):

        """Move a position to threadNext position."""

        p = self

        if p.v:
            if p.v.children:
                p.moveToFirstChild()
            elif p.hasNext():
                p.moveToNext()
            else:
                p.moveToParent()
                while p:
                    if p.hasNext():
                        p.moveToNext()
                        break #found
                    p.moveToParent()
                # not found.

        return p
    #@-node:ekr.20080416161551.209:p.moveToThreadNext
    #@+node:ekr.20080416161551.210:p.moveToVisBack
    def moveToVisBack (self,c):

        """Move a position to the position of the previous visible node."""

        trace = False and not g.unitTesting
        verbose = True
        p = self ; limit,limitIsVisible = c.visLimit()
        if trace and verbose:
            g.trace(p,'limit',limit,'limitIsVisible',limitIsVisible)
        if trace: g.trace('***entry','parent',p.parent(),'p',p,g.callers(5))
        while p:
            # Short-circuit if possible.
            back = p.back()
            if trace: g.trace(
                'back',back,'hasChildren',bool(back and back.hasChildren()),
                'isExpanded',bool(back and back.isExpanded()))

            if back and back.hasChildren() and back.isExpanded():
                p.moveToThreadBack()
            elif back:
                p.moveToBack()
            else:
                p.moveToParent() # Same as p.moveToThreadBack()
            # if back and (not back.hasChildren() or not back.isExpanded()):
                # p.moveToBack()
            # else:
                # p.moveToThreadBack()
            if trace: g.trace(p.parent(),p)
            if p:
                if trace and verbose: g.trace('**p',p)
                done,val = self.checkVisBackLimit(limit,limitIsVisible,p)
                if done:
                    if trace and verbose: g.trace('done',p)
                    return val
                if p.isVisible(c):
                    if trace and verbose: g.trace('isVisible',p)
                    return p
        else:
            # assert not p.
            return p
    #@+node:ekr.20090715145956.6166:checkVisBackLimit
    def checkVisBackLimit (self,limit,limitIsVisible,p):

        '''Return done, return-val'''

        trace = False and not g.unitTesting
        c = p.v.context

        if limit:
            if limit == p:
                if trace: g.trace('at limit',p)
                if limitIsVisible and p.isVisible(c):
                    return True,p
                else:
                    return True,None
                #return True,g.choose(limitIsVisible and p.isVisible(c),p,None)
            elif limit.isAncestorOf(p):
                return False,None
            else:
                if trace: g.trace('outside limit tree',limit,p)
                return True,None
        else:
            return False,None
    #@-node:ekr.20090715145956.6166:checkVisBackLimit
    #@-node:ekr.20080416161551.210:p.moveToVisBack
    #@+node:ekr.20080416161551.211:p.moveToVisNext
    def moveToVisNext (self,c):

        """Move a position to the position of the next visible node."""

        trace = False and not g.unitTesting
        verbose = False
        p = self ; limit,limitIsVisible = c.visLimit()
        while p:
            if trace: g.trace('1',p.h)
            # if trace: g.trace('hasChildren %s, isExpanded %s %s' % (
                # p.hasChildren(),p.isExpanded(),p.h))
            # Short-circuit if possible.
            if p.hasNext() and p.hasChildren() and p.isExpanded():
                p.moveToFirstChild()
            elif p.hasNext():
                p.moveToNext()
            else:
                p.moveToThreadNext()
            if trace: g.trace('2',p.h)
            if p:
                done,val = self.checkVisNextLimit(limit,p)
                if done: return val
                if p.isVisible(c):
                    return p.copy()
        else:
            return p
    #@+node:ekr.20090715145956.6167:checkVisNextLimit
    def checkVisNextLimit (self,limit,p):

        '''Return done, return-val'''

        trace = False and not g.unitTesting

        if limit:
            # Unlike moveToVisBack, being at the limit does not terminate.
            if limit == p:
                return False, None
            elif limit.isAncestorOf(p):
                return False,None
            else:
                if trace: g.trace('outside limit tree')
                return True,None
        else:
            return False,None
    #@-node:ekr.20090715145956.6167:checkVisNextLimit
    #@-node:ekr.20080416161551.211:p.moveToVisNext
    #@-node:ekr.20080416161551.199:p.moveToX
    #@+node:ekr.20080423062035.1:p.Low level methods
    # These methods are only for the use of low-level code
    # in leoNodes.py, leoFileCommands.py and leoUndo.py.
    #@nonl
    #@+node:ekr.20080427062528.4:p._adjustPositionBeforeUnlink
    def _adjustPositionBeforeUnlink (self,p2):

        '''Adjust position p before unlinking p2.'''

        # p will change if p2 is a previous sibling of p or
        # p2 is a previous sibling of any ancestor of p.

        trace = False and not g.unitTesting
        p = self ; sib = p.copy()

        if trace: g.trace('entry',p.stack)

        # A special case for previous siblings.
        # Adjust p._childIndex, not the stack's childIndex.
        while sib.hasBack():
            sib.moveToBack()
            if sib == p2:
                p._childIndex -= 1
                if trace: g.trace('***new index: %s\n%s' % (
                    p.h,p.stack))
                return

        # Adjust p's stack.
        stack = [] ; changed = False ; i = 0
        while i < len(p.stack):
            v,childIndex = p.stack[i]
            p3 = position(v=v,childIndex=childIndex,stack=stack[:i])
            while p3:
                if p2.v == p3.v: # A match with the to-be-moved node?
                    stack.append((v,childIndex-1),)
                    changed = True
                    break # terminate only the inner loop.
                p3.moveToBack()
            else:
                stack.append((v,childIndex),)
            i += 1

        if changed:
            if trace: g.trace('***new stack: %s\n%s' % (
                p.h,stack))
            p.stack = stack
    #@nonl
    #@-node:ekr.20080427062528.4:p._adjustPositionBeforeUnlink
    #@+node:ekr.20080416161551.214:p._linkAfter
    def _linkAfter (self,p_after,adjust=True):

        '''Link self after p_after.'''

        p = self
        parent_v = p_after._parentVnode()
            # Returns None if p.v is None

        # Init the ivars.
        p.stack = p_after.stack[:]
        p._childIndex = p_after._childIndex + 1

        # Set the links.
        child = p.v
        n = p_after._childIndex+1
        child._addLink(n,parent_v,adjust=adjust)
    #@nonl
    #@-node:ekr.20080416161551.214:p._linkAfter
    #@+node:ekr.20080416161551.215:p._linkAsNthChild
    def _linkAsNthChild (self,parent,n,adjust=True):

        p = self
        parent_v = parent.v

        # Init the ivars.
        p.stack = parent.stack[:]
        p.stack.append((parent_v,parent._childIndex),)
        p._childIndex = n

        child = p.v
        child._addLink(n,parent_v,adjust=adjust)

    #@-node:ekr.20080416161551.215:p._linkAsNthChild
    #@+node:ekr.20080416161551.212:p._parentVnode
    def _parentVnode (self):

        '''Return the parent vnode.
        Return the hiddenRootNode if there is no other parent.'''

        p = self

        if p.v:
            data = p.stack and p.stack[-1]
            if data:
                v, junk = data
                return v
            else:
                return p.v.context.hiddenRootNode
        else:
            return None
    #@-node:ekr.20080416161551.212:p._parentVnode
    #@+node:ekr.20080416161551.216:p._linkAsRoot
    def _linkAsRoot (self,oldRoot):

        """Link self as the root node."""

        p = self
        assert(p.v)

        hiddenRootNode = p.v.context.hiddenRootNode

        if oldRoot: oldRootNode = oldRoot.v
        else:       oldRootNode = None

        # Init the ivars.
        p.stack = []
        p._childIndex = 0

        parent_v = hiddenRootNode
        child = p.v
        if not oldRoot: parent_v.children = []
        child._addLink(0,parent_v)

        return p
    #@-node:ekr.20080416161551.216:p._linkAsRoot
    #@+node:ekr.20080416161551.217:p._unlink
    def _unlink (self):

        '''Unlink the receiver p from the tree.'''

        p = self ; n = p._childIndex
        parent_v = p._parentVnode()
            # returns None if p.v is None
        child = p.v
        assert(p.v)
        assert(parent_v)

        # Delete the child.
        if (0 <= n < len(parent_v.children) and
            parent_v.children[n] == child
        ):
            # This is the only call to v._cutlink.
            child._cutLink(n,parent_v)
        else:
            self.badUnlink(parent_v,n,child)
    #@nonl
    #@+node:ekr.20090706171333.6226:p.badUnlink
    def badUnlink (self,parent_v,n,child):

        if 0 <= n < len(parent_v.children):
            g.trace('**can not happen: children[%s] != p.v' % (n))
            g.trace('parent_v.children...\n',
                g.listToString(parent_v.children))
            g.trace('parent_v',parent_v)
            g.trace('parent_v.children[n]',parent_v.children[n])
            g.trace('child',child)
            g.trace('** callers:',g.callers())
            if g.app.unitTesting: assert False, 'children[%s] != p.v'
        else:   
            g.trace('**can not happen: bad child index: %s, len(children): %s' % (
                n,len(parent_v.children)))
            g.trace('parent_v.children...\n',
                g.listToString(parent_v.children))
            g.trace('parent_v',parent_v,'child',child)
            g.trace('** callers:',g.callers())
            if g.app.unitTesting: assert False, 'bad child index: %s' % (n)
    #@nonl
    #@-node:ekr.20090706171333.6226:p.badUnlink
    #@-node:ekr.20080416161551.217:p._unlink
    #@+node:ekr.20090829064400.6044:p.makeCacheList (to be removed)
    def makeCacheList(self):

        '''Create a recursive list describing a tree
        for use by v.createOutlineFromCacheList.
        '''

        p = self

        return [
            p.h,p.b,p.gnx,
            [p2.makeCacheList() for p2 in p.children()]]
    #@-node:ekr.20090829064400.6044:p.makeCacheList (to be removed)
    #@-node:ekr.20080423062035.1:p.Low level methods
    #@-others
#@-node:ekr.20031218072017.889:class position
#@+node:ville.20090311190405.68:class poslist
class poslist(list):
    """ List of positions 

    This behaves like a normal list, with the distinction that it 
    has select_h and select_b methods that can be used 
    to search through immediate children of the nodes.

    """
    #@    @+others
    #@+node:ville.20090311190405.69:select_h
    def select_h(self, regex, flags = re.IGNORECASE):
        """ Find immediate child nodes of nodes in poslist with regex.

        You can chain find_h / find_b with select_h / select_b like this
        to refine an outline search::

            pl = c.find_h('@thin.*py').select_h('class.*').select_b('import (.*)')

        """
        pat = re.compile(regex, flags)
        res = poslist()
        for p in self:
            for child_p in p.children():            
                m = re.match(pat, child_p.h)
                if m:
                    pc = child_p.copy()
                    pc.mo = m
                    res.append(pc)
        return res
    #@-node:ville.20090311190405.69:select_h
    #@+node:ville.20090311195550.1:select_b
    def select_b(self, regex, flags = re.IGNORECASE ):
        """ Find all the nodes in poslist where body matches regex

        You can chain find_h / find_b with select_h / select_b like this
        to refine an outline search::

            pl = c.find_h('@thin.*py').select_h('class.*').select_b('import (.*)')
        """
        pat = re.compile(regex, flags)
        res = poslist()
        for p in self:
            m = re.finditer(pat, p.b)
            t1,t2 = itertools.tee(m,2)
            try:
                if g.isPython3:
                    first = t1.__next__()
                else:
                    first = t1.next()
                # if does not raise StopIteration...
                pc = p.copy()
                pc.matchiter = t2
                res.append(pc)

            except StopIteration:
                pass

        return res
    #@-node:ville.20090311195550.1:select_b
    #@-others
#@-node:ville.20090311190405.68:class poslist
#@+node:ekr.20031218072017.3341:class vnode
if use_zodb and ZODB:
    class baseVnode (ZODB.Persistence.Persistent):
        pass
else:
    class baseVnode (object):
        pass

class vnode (baseVnode):
    #@    << vnode constants >>
    #@+node:ekr.20031218072017.951:<< vnode constants >>
    # Define the meaning of status bits in new vnodes.

    # Archived...
    clonedBit   = 0x01 # True: vnode has clone mark.
    # unused      0x02
    expandedBit = 0x04 # True: vnode is expanded.
    markedBit   = 0x08 # True: vnode is marked
    orphanBit   = 0x10 # True: vnode saved in .leo file, not derived file.
    selectedBit = 0x20 # True: vnode is current vnode.
    topBit      = 0x40 # True: vnode was top vnode when saved.

    # Not archived...
    richTextBit = 0x080 # Determines whether we use <bt> or <btr> tags.
    visitedBit  = 0x100
    dirtyBit    = 0x200
    writeBit    = 0x400
    #@-node:ekr.20031218072017.951:<< vnode constants >>
    #@nl
    #@    @+others
    #@+node:ekr.20031218072017.3342:v.Birth & death
    #@+node:ekr.20031218072017.3344:v.__init
    # To support ZODB, the code must set v._p_changed = 1 whenever
    # v.unknownAttributes or any mutable vnode object changes.

    def __init__ (self,context):

        # The primary data: headline and body text.
        self._headString = g.u('newHeadline')
        self._bodyString = g.u('')

        # Structure data...
        self.children = [] # Ordered list of all children of this node.
        self.parents = [] # Unordered list of all parents of this node.

        # Other essential data...
        self.fileIndex = g.app.nodeIndices.getNewIndex()
            # The immutable file index for this vnode.
            # New in Leo 4.6 b2: allocate gnx (fileIndex) immediately.
        self.iconVal = 0 # The present value of the node's icon.
        self.statusBits = 0 # status bits

        # v.t no longer exists.  All code must now be aware of the one-node world.
        # self.t = self # For compatibility with scripts and plugins.

        # Information that is never written to any file...
        self.context = context # The context containing context.hiddenRootNode.
            # Required so we can compute top-level siblings.
            # It is named .context rather than .c to emphasize its limited usage.
        self.insertSpot = None # Location of previous insert point.
        self.scrollBarSpot = None # Previous value of scrollbar position.
        self.selectionLength = 0 # The length of the selected body text.
        self.selectionStart = 0 # The start of the selected body text.
    #@-node:ekr.20031218072017.3344:v.__init
    #@+node:ekr.20031218072017.3345:v.__repr__ & v.__str__
    def __repr__ (self):

        return "<vnode %d:'%s'>" % (id(self),self.cleanHeadString())

    __str__ = __repr__
    #@-node:ekr.20031218072017.3345:v.__repr__ & v.__str__
    #@+node:ekr.20040312145256:v.dump
    def dumpLink (self,link):
        return g.choose(link,link,"<none>")

    def dump (self,label=""):

        v = self
        print('%s %s %s' % ('-'*10,label,v))
        print('len(parents) %s' % len(v.parents))
        print('len(children) %s' % len(v.children))
        print('parents %s' % g.listToString(v.parents))
        print('children%s' % g.listToString(v.children))
    #@-node:ekr.20040312145256:v.dump
    #@+node:ekr.20060910100316:v.__hash__ (only for zodb)
    if use_zodb and ZODB:
        def __hash__(self):
            return self.__hash__()
    #@nonl
    #@-node:ekr.20060910100316:v.__hash__ (only for zodb)
    #@-node:ekr.20031218072017.3342:v.Birth & death
    #@+node:ekr.20031218072017.3346:v.Comparisons
    #@+node:ekr.20040705201018:v.findAtFileName
    def findAtFileName (self,names,h=''):

        """Return the name following one of the names in nameList.
        Return an empty string."""

        # Allow h argument for unit testing.
        if not h: h = self.headString()

        if not g.match(h,0,'@'):
            return ""

        i = g.skip_id(h,1,'-')
        word = h[:i]
        if word in names and g.match_word(h,0,word):
            name = h[i:].strip()
            # g.trace(repr(word),repr(name))
            return name
        else:
            return ""
    #@-node:ekr.20040705201018:v.findAtFileName
    #@+node:ekr.20031218072017.3350:anyAtFileNodeName
    def anyAtFileNodeName (self):

        """Return the file name following an @file node or an empty string."""

        names = (
            "@auto",
            "@auto-rst",
            "@edit",
            "@file",
            "@thin",   "@file-thin",   "@thinfile",
            "@asis",   "@file-asis",   "@silentfile",
            "@nosent", "@file-nosent", "@nosentinelsfile",
            "@shadow",)

        return self.findAtFileName(names)
    #@-node:ekr.20031218072017.3350:anyAtFileNodeName
    #@+node:ekr.20031218072017.3348:at...FileNodeName
    # These return the filename following @xxx, in v.headString.
    # Return the the empty string if v is not an @xxx node.

    def atAutoNodeName (self,h=None):
        # # Prevent conflicts with autotrees plugin: don't allow @auto-whatever to match.
        # return g.match_word(h,0,tag) and not g.match(h,0,tag+'-') and h[len(tag):].strip()
        names = ("@auto","@auto-rst",)
        return self.findAtFileName(names,h=h)

    def atAutoRstNodeName (self,h=None):
        names = ("@auto-rst",)
        return self.findAtFileName(names,h=h)

    def atEditNodeName (self):
        names = ("@edit",)
        return self.findAtFileName(names)

    def atFileNodeName (self):
        names = ("@file",)
        return self.findAtFileName(names)

    def atNoSentinelsFileNodeName (self):
        names = ("@nosent", "@file-nosent", "@nosentinelsfile")
        return self.findAtFileName(names)

    def atShadowFileNodeName (self):
        names = ("@shadow",)
        return self.findAtFileName(names)

    def atSilentFileNodeName (self):
        names = ("@asis", "@file-asis", "@silentfile")
        return self.findAtFileName(names)

    def atThinFileNodeName (self):
        names = ("@thin", "@file-thin", "@thinfile")
        return self.findAtFileName(names)

    # New names, less confusing
    atNoSentFileNodeName  = atNoSentinelsFileNodeName
    atAsisFileNodeName    = atSilentFileNodeName
    #@-node:ekr.20031218072017.3348:at...FileNodeName
    #@+node:EKR.20040430152000:isAtAllNode
    def isAtAllNode (self):

        """Returns True if the receiver contains @others in its body at the start of a line."""

        flag, i = g.is_special(self._bodyString,0,"@all")
        return flag
    #@-node:EKR.20040430152000:isAtAllNode
    #@+node:ekr.20040326031436:isAnyAtFileNode
    def isAnyAtFileNode (self):

        """Return True if v is any kind of @file or related node."""

        # This routine should be as fast as possible.
        # It is called once for every vnode when writing a file.

        h = self.headString()
        return h and h[0] == '@' and self.anyAtFileNodeName()
    #@-node:ekr.20040326031436:isAnyAtFileNode
    #@+node:ekr.20040325073709:isAt...FileNode (vnode)
    def isAtAutoNode (self):
        return g.choose(self.atAutoNodeName(),True,False)

    def isAtAutoRstNode (self):
        return g.choose(self.atAutoRstNodeName(),True,False)

    def isAtEditNode (self):
        return g.choose(self.atEditNodeName(),True,False)

    def isAtFileNode (self):
        return g.choose(self.atFileNodeName(),True,False)

    def isAtNoSentinelsFileNode (self):
        return g.choose(self.atNoSentinelsFileNodeName(),True,False)

    def isAtSilentFileNode (self): # @file-asis
        return g.choose(self.atSilentFileNodeName(),True,False)

    def isAtShadowFileNode (self):
        return g.choose(self.atShadowFileNodeName(),True,False)

    def isAtThinFileNode (self):
        return g.choose(self.atThinFileNodeName(),True,False)

    # New names, less confusing:
    isAtNoSentFileNode = isAtNoSentinelsFileNode
    isAtAsisFileNode   = isAtSilentFileNode
    #@-node:ekr.20040325073709:isAt...FileNode (vnode)
    #@+node:ekr.20031218072017.3351:isAtIgnoreNode
    def isAtIgnoreNode (self):

        """Returns True if the receiver contains @ignore in its body at the start of a line."""

        flag, i = g.is_special(self._bodyString, 0, "@ignore")
        return flag
    #@-node:ekr.20031218072017.3351:isAtIgnoreNode
    #@+node:ekr.20031218072017.3352:isAtOthersNode
    def isAtOthersNode (self):

        """Returns True if the receiver contains @others in its body at the start of a line."""

        flag, i = g.is_special(self._bodyString,0,"@others")
        return flag
    #@-node:ekr.20031218072017.3352:isAtOthersNode
    #@+node:ekr.20031218072017.3353:matchHeadline
    def matchHeadline (self,pattern):

        """Returns True if the headline matches the pattern ignoring whitespace and case.

        The headline may contain characters following the successfully matched pattern."""

        v = self

        h = g.toUnicode(v.headString())
        h = h.lower().replace(' ','').replace('\t','')

        pattern = g.toUnicode(pattern)
        pattern = pattern.lower().replace(' ','').replace('\t','')

        return h.startswith(pattern)
    #@-node:ekr.20031218072017.3353:matchHeadline
    #@-node:ekr.20031218072017.3346:v.Comparisons
    #@+node:ekr.20031218072017.3359:v.Getters
    #@+node:ekr.20031218072017.3378:v.bodyString
    def bodyString (self):

        # This message should never be printed and we want to avoid crashing here!
        if g.isUnicode(self._bodyString):
            return self._bodyString
        else:
            g.internalError('not unicode:',repr(self._bodyString))
            return g.toUnicode(self._bodyString)

    getBody = bodyString
    #@nonl
    #@-node:ekr.20031218072017.3378:v.bodyString
    #@+node:ekr.20031218072017.3360:v.Children
    #@+node:ekr.20031218072017.3362:v.firstChild
    def firstChild (self):

        v = self
        return v.children and v.children[0]
    #@-node:ekr.20031218072017.3362:v.firstChild
    #@+node:ekr.20040307085922:v.hasChildren & hasFirstChild
    def hasChildren (self):

        v = self
        return len(v.children) > 0

    hasFirstChild = hasChildren
    #@-node:ekr.20040307085922:v.hasChildren & hasFirstChild
    #@+node:ekr.20031218072017.3364:v.lastChild
    def lastChild (self):

        v = self
        return v.children and v.children[-1] or None
    #@-node:ekr.20031218072017.3364:v.lastChild
    #@+node:ekr.20031218072017.3365:v.nthChild
    # childIndex and nthChild are zero-based.

    def nthChild (self, n):

        v = self

        if 0 <= n < len(v.children):
            return v.children[n]
        else:
            return None
    #@-node:ekr.20031218072017.3365:v.nthChild
    #@+node:ekr.20031218072017.3366:v.numberOfChildren
    def numberOfChildren (self):

        v = self
        return len(v.children)
    #@-node:ekr.20031218072017.3366:v.numberOfChildren
    #@-node:ekr.20031218072017.3360:v.Children
    #@+node:ekr.20040323100443:v.directParents
    def directParents (self):

        """(New in 4.2) Return a list of all direct parent vnodes of a vnode.

        This is NOT the same as the list of ancestors of the vnode."""

        v = self
        return v.parents
    #@-node:ekr.20040323100443:v.directParents
    #@+node:ekr.20080429053831.6:v.hasBody
    def hasBody (self):

        '''Return True if this vnode contains body text.'''

        s = self._bodyString

        return s and len(s) > 0
    #@-node:ekr.20080429053831.6:v.hasBody
    #@+node:ekr.20031218072017.1581:v.headString & v.cleanHeadString
    def headString (self):

        """Return the headline string."""

        # This message should never be printed and we want to avoid crashing here!
        if not g.isUnicode(self._headString):
            g.internalError('not unicode',repr(self._headString))

        # Make _sure_ we return a unicode string.
        return g.toUnicode(self._headString)

    def cleanHeadString (self):

        s = self._headString
        return g.toEncodedString(s,"ascii") # Replaces non-ascii characters by '?'
    #@-node:ekr.20031218072017.1581:v.headString & v.cleanHeadString
    #@+node:ekr.20031218072017.3367:v.Status Bits
    #@+node:ekr.20031218072017.3368:v.isCloned
    def isCloned (self):

        return len(self.parents) > 1
    #@-node:ekr.20031218072017.3368:v.isCloned
    #@+node:ekr.20031218072017.3369:v.isDirty
    def isDirty (self):

        return (self.statusBits & self.dirtyBit) != 0
    #@-node:ekr.20031218072017.3369:v.isDirty
    #@+node:ekr.20031218072017.3370:v.isExpanded
    def isExpanded (self):

        # g.trace( ( self.statusBits & self.expandedBit ) != 0, g.callers())

        return ( self.statusBits & self.expandedBit ) != 0
    #@-node:ekr.20031218072017.3370:v.isExpanded
    #@+node:ekr.20031218072017.3371:v.isMarked
    def isMarked (self):

        return ( self.statusBits & vnode.markedBit ) != 0
    #@-node:ekr.20031218072017.3371:v.isMarked
    #@+node:ekr.20031218072017.3372:v.isOrphan
    def isOrphan (self):

        return ( self.statusBits & vnode.orphanBit ) != 0
    #@-node:ekr.20031218072017.3372:v.isOrphan
    #@+node:ekr.20031218072017.3373:v.isSelected
    def isSelected (self):

        return ( self.statusBits & vnode.selectedBit ) != 0
    #@-node:ekr.20031218072017.3373:v.isSelected
    #@+node:ekr.20031218072017.3374:v.isTopBitSet
    def isTopBitSet (self):

        return ( self.statusBits & self.topBit ) != 0
    #@-node:ekr.20031218072017.3374:v.isTopBitSet
    #@+node:ekr.20031218072017.3376:v.isVisited
    def isVisited (self):

        return ( self.statusBits & vnode.visitedBit ) != 0
    #@-node:ekr.20031218072017.3376:v.isVisited
    #@+node:ekr.20080429053831.10:v.isWriteBit
    def isWriteBit (self):

        v = self
        return (v.statusBits & v.writeBit) != 0
    #@-node:ekr.20080429053831.10:v.isWriteBit
    #@+node:ekr.20031218072017.3377:v.status
    def status (self):

        return self.statusBits
    #@-node:ekr.20031218072017.3377:v.status
    #@-node:ekr.20031218072017.3367:v.Status Bits
    #@-node:ekr.20031218072017.3359:v.Getters
    #@+node:ekr.20031218072017.3384:v.Setters
    #@+node:ekr.20090830051712.6151: v.Dirty bits
    #@+node:ekr.20031218072017.3390:v.clearDirty
    def clearDirty (self):
        v = self
        v.statusBits &= ~ v.dirtyBit

    #@-node:ekr.20031218072017.3390:v.clearDirty
    #@+node:ekr.20090830051712.6153:v.findAllPotentiallyDirtyNodes
    def findAllPotentiallyDirtyNodes(self):

        trace = False and not g.unitTesting
        v = self ; c = v.context

        # Set the starting nodes.
        nodes = []
        newNodes = [v]

        # Add nodes until no more are added.
        while newNodes:
            addedNodes = []
            nodes.extend(newNodes)
            for v in newNodes:
                for v2 in v.parents:
                    if v2 not in nodes and v2 not in addedNodes:
                        addedNodes.append(v2)
            newNodes = addedNodes[:]

        # Remove the hidden vnode.
        if c.hiddenRootNode in nodes:
            if trace: g.trace('removing hidden root',c.hiddenRootNode)
            nodes.remove(c.hiddenRootNode)

        if trace: g.trace(nodes)
        return nodes
    #@nonl
    #@-node:ekr.20090830051712.6153:v.findAllPotentiallyDirtyNodes
    #@+node:ekr.20090830051712.6157:v.setAllAncestorAtFileNodesDirty
    # Unlike p.setAllAncestorAtFileNodesDirty,
    # there is no setDescendentsDirty arg.

    def setAllAncestorAtFileNodesDirty (self):

        trace = False and not g.unitTesting
        verbose = False
        v = self
        dirtyVnodeList = []

        # Calculate all nodes that are joined to p or parents of such nodes.
        nodes = v.findAllPotentiallyDirtyNodes()

        if trace and verbose:
            for v in nodes:
                print (v.isDirty(),v.isAnyAtFileNode(),v)

        dirtyVnodeList = [v for v in nodes
            if not v.isDirty() and v.isAnyAtFileNode()]

        changed = len(dirtyVnodeList) > 0

        for v in dirtyVnodeList:
            v.setDirty() # Do not call v.setDirty here!

        if trace: g.trace("vnode",dirtyVnodeList)

        return dirtyVnodeList
    #@-node:ekr.20090830051712.6157:v.setAllAncestorAtFileNodesDirty
    #@+node:ekr.20080429053831.12:v.setDirty
    def setDirty (self):

        self.statusBits |= self.dirtyBit
    #@-node:ekr.20080429053831.12:v.setDirty
    #@-node:ekr.20090830051712.6151: v.Dirty bits
    #@+node:ekr.20031218072017.3386: v.Status bits
    #@+node:ekr.20031218072017.3389:v.clearClonedBit
    def clearClonedBit (self):

        self.statusBits &= ~ self.clonedBit
    #@-node:ekr.20031218072017.3389:v.clearClonedBit
    #@+node:ekr.20031218072017.3391:v.clearMarked
    def clearMarked (self):

        self.statusBits &= ~ self.markedBit
    #@-node:ekr.20031218072017.3391:v.clearMarked
    #@+node:ekr.20080429053831.8:v.clearWriteBit
    def clearWriteBit (self):
        self.statusBits &= ~ self.writeBit
    #@-node:ekr.20080429053831.8:v.clearWriteBit
    #@+node:ekr.20031218072017.3392:v.clearOrphan
    def clearOrphan (self):

        self.statusBits &= ~ self.orphanBit
    #@-node:ekr.20031218072017.3392:v.clearOrphan
    #@+node:ekr.20031218072017.3393:v.clearVisited
    def clearVisited (self):

        self.statusBits &= ~ self.visitedBit
    #@-node:ekr.20031218072017.3393:v.clearVisited
    #@+node:ekr.20031218072017.3395:v.contract & expand & initExpandedBit
    def contract(self):

        # if self.context.p.v == self: g.trace(self,g.callers(4))

        self.statusBits &= ~ self.expandedBit

    def expand(self):

        # g.trace(self,g.callers(4))

        self.statusBits |= self.expandedBit

    def initExpandedBit (self):

        # g.trace(self._headString)

        self.statusBits |= self.expandedBit
    #@-node:ekr.20031218072017.3395:v.contract & expand & initExpandedBit
    #@+node:ekr.20031218072017.3396:v.initStatus
    def initStatus (self, status):

        self.statusBits = status
    #@-node:ekr.20031218072017.3396:v.initStatus
    #@+node:ekr.20031218072017.3397:v.setClonedBit & initClonedBit
    def setClonedBit (self):

        self.statusBits |= self.clonedBit

    def initClonedBit (self, val):

        if val:
            self.statusBits |= self.clonedBit
        else:
            self.statusBits &= ~ self.clonedBit
    #@-node:ekr.20031218072017.3397:v.setClonedBit & initClonedBit
    #@+node:ekr.20031218072017.3398:v.setMarked & initMarkedBit
    def setMarked (self):

        self.statusBits |= self.markedBit

    def initMarkedBit (self):

        self.statusBits |= self.markedBit
    #@-node:ekr.20031218072017.3398:v.setMarked & initMarkedBit
    #@+node:ekr.20031218072017.3399:v.setOrphan
    def setOrphan (self):

        self.statusBits |= self.orphanBit
    #@-node:ekr.20031218072017.3399:v.setOrphan
    #@+node:ekr.20031218072017.3400:v.setSelected
    # This only sets the selected bit.

    def setSelected (self):

        self.statusBits |= self.selectedBit
    #@-node:ekr.20031218072017.3400:v.setSelected
    #@+node:ekr.20031218072017.3401:v.setVisited
    # Compatibility routine for scripts

    def setVisited (self):

        self.statusBits |= self.visitedBit
    #@-node:ekr.20031218072017.3401:v.setVisited
    #@+node:ekr.20080429053831.9:v.setWriteBit
    def setWriteBit (self):
        self.statusBits |= self.writeBit
    #@-node:ekr.20080429053831.9:v.setWriteBit
    #@-node:ekr.20031218072017.3386: v.Status bits
    #@+node:ekr.20040315032144:v .setBodyString & v.setHeadString
    def setBodyString (self,s):

        # trace = False and not g.unitTesting
        v = self
        # if trace and v._bodyString != s:
            # g.trace('v %s %s -> %s %s\nold: %s\nnew: %s' % (
                # v.h, len(v._bodyString),len(s),g.callers(5),
                # v._bodyString,s))
        v._bodyString = g.toUnicode(s,reportErrors=True)

    def setHeadString (self,s):
        v = self
        v._headString = g.toUnicode(s,reportErrors=True)

    initBodyString = setBodyString
    initHeadString = setHeadString
    setHeadText = setHeadString
    setTnodeText = setBodyString
    #@-node:ekr.20040315032144:v .setBodyString & v.setHeadString
    #@+node:ekr.20080429053831.13:v.setFileIndex
    def setFileIndex (self, index):

        self.fileIndex = index
    #@-node:ekr.20080429053831.13:v.setFileIndex
    #@+node:ekr.20031218072017.3385:v.computeIcon & setIcon
    def computeIcon (self):

        val = 0 ; v = self
        if v.hasBody(): val += 1
        if v.isMarked(): val += 2
        if v.isCloned(): val += 4
        if v.isDirty(): val += 8
        return val

    def setIcon (self):

        pass # Compatibility routine for old scripts
    #@-node:ekr.20031218072017.3385:v.computeIcon & setIcon
    #@+node:ekr.20031218072017.3402:v.setSelection
    def setSelection (self, start, length):

        v = self
        v.selectionStart = start
        v.selectionLength = length
    #@-node:ekr.20031218072017.3402:v.setSelection
    #@-node:ekr.20031218072017.3384:v.Setters
    #@+node:ekr.20080427062528.9:v.Low level methods
    #@+node:ekr.20090706110836.6135:v._addLink & helper
    def _addLink (self,childIndex,parent_v,adjust=True):
        '''Adjust links after adding a link to v.'''

        trace = False and not g.unitTesting
        v = self

        # Update parent_v.children & v.parents.
        parent_v.children.insert(childIndex,v)
        v.parents.append(parent_v)
        if trace: g.trace('*** added parent',parent_v,'to',v,
            'len(parents)',len(v.parents))

        # Set zodb changed flags.
        v._p_changed = 1
        parent_v._p_changed = 1

        # If v has only one parent, we adjust all
        # the parents links in the descendant tree.
        # This handles clones properly when undoing a delete.
        if adjust:
            if len(v.parents) == 1:
                for child in v.children:
                    child._addParentLinks(parent=v)
    #@+node:ekr.20090804184658.6129:v._addParentLinks
    def _addParentLinks(self,parent): 

        trace = False and not g.unitTesting
        v = self

        v.parents.append(parent)
        if trace: g.trace(
            '*** added parent',parent,'to',v,'len(parents)',len(v.parents))

        if len(v.parents) == 1:
            for child in v.children:
                child._addParentLinks(parent=v)
    #@nonl
    #@-node:ekr.20090804184658.6129:v._addParentLinks
    #@-node:ekr.20090706110836.6135:v._addLink & helper
    #@+node:ekr.20090804184658.6128:v._cutLink
    def _cutLink (self,childIndex,parent_v):
        '''Adjust links after cutting a link to v.'''
        v = self

        assert parent_v.children[childIndex]==v
        del parent_v.children[childIndex]
        v.parents.remove(parent_v)
        v._p_changed = 1
        parent_v._p_changed = 1

        # If v has no more parents, we adjust all
        # the parent links in the descendant tree.
        # This handles clones properly when deleting a tree.
        if len(v.parents) == 0:
            for child in v.children:
                child._cutParentLinks(parent=v)
    #@nonl
    #@+node:ekr.20090804190529.6133:v._cutParentLinks
    def _cutParentLinks(self,parent):

        trace = False and not g.unitTesting
        v = self

        if trace: g.trace('parent',parent,'v',v)
        v.parents.remove(parent)

        if len(v.parents) == 0:
            for child in v.children:
                child._cutParentLinks(parent=v)
    #@-node:ekr.20090804190529.6133:v._cutParentLinks
    #@-node:ekr.20090804184658.6128:v._cutLink
    #@+node:ekr.20031218072017.3425:v._linkAsNthChild (used by 4.x read logic)
    def _linkAsNthChild (self,parent_v,n):

        """Links self as the n'th child of vnode pv"""

        v = self # The child node.
        v._addLink(n,parent_v)
    #@-node:ekr.20031218072017.3425:v._linkAsNthChild (used by 4.x read logic)
    #@+node:ekr.20090829064400.6040:v.createOutlineFromCacheList & helpers (to be removed)
    def createOutlineFromCacheList(self,c,aList,top=True,atAll=None,fileName=None):
        """ Create outline structure from recursive aList
        built by p.makeCacheList.

        Clones will be automatically created by gnx,
        but *not* for the top-level node.
        """

        trace = False and not g.unitTesting
        parent_v = self

        #import pprint ; pprint.pprint(tree)
        parent_v = self
        h,b,gnx,children = aList
        if h is not None:
            v = parent_v
            v._headString = h    
            v._bodyString = b

        if top:
            c.cacheListFileName = fileName
            # Scan the body for @all directives.
            for line in g.splitLines(b):
                if line.startswith('@all'):
                    atAll = True ; break
            else:
                atAll = False
        else:
            assert atAll in (True,False,)

        for z in children:
            h,b,gnx,grandChildren = z
            isClone,child_v = parent_v.fastAddLastChild(c,gnx)
            if isClone:
                if child_v.b != b:
                    # 2010/02/05: Remove special case for @all.
                    c.nodeConflictList.append(g.bunch(
                        tag='(cached)',
                        fileName=c.cacheListFileName,
                        gnx=gnx,
                        b_old=child_v.b,
                        h_old=child_v.h,
                        b_new=b,
                        h_new=h,
                    ))

                    # Always issue the warning.
                    g.es_print("cached read node changed:",
                        child_v.h,color="red")

                    child_v.h,child_v.b = h,b
                    child_v.setDirty()
                    c.changed = True
                        # Tells getLeoFile to propegate dirty nodes.
            else:
                child_v.createOutlineFromCacheList(c,z,top=False,atAll=atAll)
    #@+node:ekr.20090829064400.6042:v.fastAddLastChild
    # Similar to createThinChild4
    def fastAddLastChild(self,c,gnxString):
        '''Create new vnode as last child of the receiver.

        If the gnx exists already, create a clone instead of new vnode.
        '''

        trace = False and not g.unitTesting
        verbose = False
        parent_v = self
        indices = g.app.nodeIndices
        gnxDict = c.fileCommands.gnxDict

        if gnxString is None: v = None
        else:                 v = gnxDict.get(gnxString)
        is_clone = v is not None

        if trace: g.trace(
            'clone','%-5s' % (is_clone),
            'parent_v',parent_v,'gnx',gnxString,'v',repr(v))

        if is_clone:
            pass
        else:
            v = vnode(context=c)
            if gnxString:
                gnx = indices.scanGnx(gnxString,0)
                v.fileIndex = gnx
            gnxDict[gnxString] = v

        child_v = v
        child_v._linkAsNthChild(parent_v,parent_v.numberOfChildren())
        child_v.setVisited() # Supress warning/deletion of unvisited nodes.

        return is_clone,child_v
    #@-node:ekr.20090829064400.6042:v.fastAddLastChild
    #@-node:ekr.20090829064400.6040:v.createOutlineFromCacheList & helpers (to be removed)
    #@-node:ekr.20080427062528.9:v.Low level methods
    #@+node:ekr.20090130065000.1:v.Properties
    #@+node:ekr.20090130114732.5:v.b Property
    def __get_b(self):

        v = self
        return v.bodyString()

    def __set_b(self,val):

        v = self
        v.setBodyString(val)

    b = property(
        __get_b, __set_b,
        doc = "vnode body string property")
    #@-node:ekr.20090130114732.5:v.b Property
    #@+node:ekr.20090130125002.1:v.h property
    def __get_h(self):

        v = self
        return v.headString()

    def __set_h(self,val):

        v = self
        v.setHeadString(val)

    h = property(
        __get_h, __set_h,
        doc = "vnode headline string property")  
    #@-node:ekr.20090130125002.1:v.h property
    #@+node:ekr.20090130114732.6:v.u Property
    def __get_u(self):
        v = self
        if not hasattr(v,'unknownAttributes'):
            v.unknownAttributes = {}
        return v.unknownAttributes

    def __set_u(self,val):
        v = self
        if val is None:
            if hasattr(v,'unknownAttributes'):
                delattr(v,'unknownAttributes')
        elif type(val) == type({}):
            v.unknownAttributes = val
        else:
            raise ValueError

    u = property(
        __get_u, __set_u,
        doc = "vnode unknownAttribute property")
    #@-node:ekr.20090130114732.6:v.u Property
    #@+node:ekr.20090215165030.1:v.gnx Property
    def __get_gnx(self):
        v = self
        return g.app.nodeIndices.toString(v.fileIndex)

    gnx = property(
        __get_gnx, # __set_gnx,
        doc = "vnode gnx property")
    #@-node:ekr.20090215165030.1:v.gnx Property
    #@-node:ekr.20090130065000.1:v.Properties
    #@-others
#@nonl
#@-node:ekr.20031218072017.3341:class vnode
#@-others
#@nonl
#@-node:ekr.20031218072017.3320:@thin leoNodes.py
#@-leo
