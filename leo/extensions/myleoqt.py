#@+leo-ver=5-thin
#@+node:vitalije.20200502083732.1: * @file myleoqt.py
#@@language python
#@@tabwidth -4
LEO_INSTALLED_AT = '/opt/programi/leo/trunk'
#@+<<imports>>
#@+node:vitalije.20200502091628.1: ** <<imports>>
import sqlite3
import sys
if LEO_INSTALLED_AT not in sys.path:
    sys.path.append(LEO_INSTALLED_AT)
import leo.core.leoNodes as leoNodes
import leo.core.leoGlobals as g
g.app = g.bunch(nodeIndices=leoNodes.NodeIndices('vitalije'))
from PyQt5 import QtCore, QtGui, QtWidgets
assert QtGui
Q = QtCore.Qt
import pickle
#@-<<imports>>
#@+others
#@+node:vitalije.20200502090425.1: ** DummyLeoController
class DummyLeoController:
    def __init__(self, fname):
        self.fileCommands = self
        self.gnxDict = {}
        self.mFileName = fname
        self.c = self
        self.hiddenRootNode = leoNodes.VNode(self, 'hidden-root-vnode-gnx')
        conn = sqlite3.connect(fname)
        self.retrieveVnodesFromDb(conn)
        self.guiapi = g.bunch(
            body = None,
            tree = None,
            resetBody = None,
            resetHeadline = None,
            treeSelector = None
        )
        self.undoBeads = []
        self.undoPos = 0

    #@+others
    #@+node:vitalije.20200502090418.1: *3* retrieveVnodesFromDb
    # this is just copy pasted from leoFileCommands
    def retrieveVnodesFromDb(self, conn):
        """
        Recreates tree from the data contained in table vnodes.
        
        This method follows behavior of readSaxFile.
        """

        c, fc = self.c, self
        sql = '''select gnx, head, 
             body,
             children,
             parents,
             iconVal,
             statusBits,
             ua from vnodes'''
        vnodes = []
        try:
            for row in conn.execute(sql):
                (gnx, h, b, children, parents, iconVal, statusBits, ua) = row
                try:
                    ua = pickle.loads(g.toEncodedString(ua))
                except ValueError:
                    ua = None
                v = leoNodes.VNode(context=c, gnx=gnx)
                v._headString = h
                v._bodyString = b
                v.children = children.split()
                v.parents = parents.split()
                v.iconVal = iconVal
                v.statusBits = statusBits
                v.expand()
                v.u = ua
                vnodes.append(v)
        except sqlite3.Error as er:
            if er.args[0].find('no such table') < 0:
                # there was an error raised but it is not the one we expect
                g.internalError(er)
            # there is no vnodes table
            return None

        rootChildren = [x for x in vnodes if 'hidden-root-vnode-gnx' in x.parents]
        if not rootChildren:
            g.trace('there should be at least one top level node!')
            return None

        findNode = lambda x: fc.gnxDict.get(x, c.hiddenRootNode)

        # let us replace every gnx with the corresponding vnode
        for v in vnodes:
            v.children = [findNode(x) for x in v.children]
            v.parents = [findNode(x) for x in v.parents]
        c.hiddenRootNode.children = rootChildren
        return rootChildren[0]
    #@+node:vitalije.20200502090418.2: *4* fc.initNewDb
    def initNewDb(self, conn):
        """ Initializes tables and returns None"""
        fc = self; c = self.c
        v = leoNodes.VNode(context=c)
        c.hiddenRootNode.children = [v]
        (w, h, x, y, r1, r2, encp) = fc.getWindowGeometryFromDb(conn)
        c.frame.setTopGeometry(w, h, x, y)
        c.frame.resizePanesToRatio(r1, r2)
        c.sqlite_connection = conn
        fc.exportToSqlite(c.mFileName)
        return v
    #@+node:vitalije.20200502090418.3: *4* fc.getWindowGeometryFromDb
    def getWindowGeometryFromDb(self, conn):
        geom = (600, 400, 50, 50, 0.5, 0.5, '')
        keys = ('width', 'height', 'left', 'top',
                  'ratio', 'secondary_ratio',
                  'current_position')
        try:
            d = dict(
                conn.execute(
                '''select * from extra_infos 
                where name in (?, ?, ?, ?, ?, ?, ?)''',
                keys,
            ).fetchall(),
            )
            geom = (d.get(*x) for x in zip(keys, geom))
        except sqlite3.OperationalError:
            pass
        return geom
    #@+node:vitalije.20200503144746.1: *3* undo/redo
    def canUndo(self):
        return self.undoPos > 0

    def canRedo(self):
        return self.undoPos < len(self.undoBeads)

    def addUndo(self, u, r):
        i = self.undoPos
        self.undoBeads[i:] = [g.bunch(undo=u, redo=r)]
        self.undoPos += 1
        self.guiapi.updateToolbarButtons()

    def undo(self):
        if self.canUndo():
            self.undoPos -= 1
            ub = self.undoBeads[self.undoPos]
            ub.undo()
            self.guiapi.updateToolbarButtons()

    def redo(self):
        if self.canRedo():
            ub = self.undoBeads[self.undoPos]
            self.undoPos += 1
            ub.redo()
            self.guiapi.updateToolbarButtons()
    #@+node:vitalije.20200503181122.1: *3* setCurrentNode
    def setCurrentNode(self, v):
        self._p = g.bunch(v=v)
        self.guiapi.resetBody(v.b)
    #@+node:vitalije.20200503181125.1: *3* updateBody
    def updateBody(self, b):
        self._p.v.b = b
    #@+node:vitalije.20200503181127.1: *3* updateHeadline
    def updateHeadline(self, h):
        self._p.v.h = h
    #@+node:vitalije.20200503181130.1: *3* getCurrentPosition
    def getCurrentPosition(self):
        return self._p
    p = property(getCurrentPosition)
    #@-others
#@+node:vitalije.20200502090833.1: ** MyGUI
class MyGUI(QtWidgets.QApplication):
    def __init__(self, c):
        QtWidgets.QApplication.__init__(self, [])
        self.c = c
        self.hoistStack = []
    #@+others
    #@+node:vitalije.20200502142944.1: *3* create_main_window
    def create_main_window(self):
        self.mw = QtWidgets.QMainWindow()
        self.mw.resize(800, 600)
        dock_l = QtWidgets.QDockWidget(self.mw)
        self.tree = QtWidgets.QTreeWidget(dock_l)
        dock_l.setWidget(self.tree)
        self.tree.setHeaderHidden(True)
        self.tree.setSelectionMode(self.tree.SingleSelection)
        draw_tree(self.tree, self.c.hiddenRootNode)
        self.tree.currentItemChanged.connect(self.select_item)
        self.tree.itemChanged.connect(self.update_headline)
        self.mw.addDockWidget(Q.LeftDockWidgetArea, dock_l, Q.Vertical)
        self.body = QtWidgets.QTextBrowser(self.mw)
        self.body.setReadOnly(False)
        self.body.textChanged.connect(self.body_changed)
        self.mw.setCentralWidget(self.body)
        self.create_toolbar()
        self.mw.show()
        c = self.c
        c.guiapi = self
    #@+node:vitalije.20200503181324.1: *3* create_toolbar
    def create_toolbar(self):
        dock_t = QtWidgets.QDockWidget(self.mw)
        self.toolbar = QtWidgets.QToolBar(dock_t)
        dock_t.setWidget(self.toolbar)
        self.mw.addDockWidget(Q.TopDockWidgetArea, dock_t, Q.Horizontal)
        self.toolbar.addAction('up', self.move_node_up)
        self.toolbar.addAction('down', self.move_node_down)
        self.toolbar.addAction('left', self.move_node_left)
        self.toolbar.addAction('right', self.move_node_right)
        self.toolbar.addAction('promote', self.promote)
        self.toolbar.addAction('demote', self.demote)
        self.hoistAction = self.toolbar.addAction('hoist', self.set_hoist)
        self.dehoistAction = self.toolbar.addAction('dehoist', self.unset_hoist)
        self.undoAction = self.toolbar.addAction('undo', self.c.undo)
        self.redoAction = self.toolbar.addAction('redo', self.c.redo)
        self.updateToolbarButtons()
    #@+node:vitalije.20200503154834.1: *3* hoist/dehoist
    def set_hoist(self):
        t = self.tree
        curr = t.currentItem()
        if curr.childCount():
            self.hoistStack.append(t.rootIndex())
            if curr.text(0).startswith('@chapter '):
                ind = t.indexFromItem(curr)
                t.setRootIndex(ind)
                t.setCurrentItem(curr.child(0))
            else:
                par = curr.parent() or t.invisibleRootItem()
                ind = t.indexFromItem(par)
                t.setRootIndex(ind)
                for i in range(par.childCount()):
                    ch = par.child(i)
                    ch.setHidden(curr != ch)
            self.updateToolbarButtons()

    def unset_hoist(self):
        t = self.tree
        if not self.hoistStack:
            return
        item = t.itemFromIndex(t.rootIndex()) or t.invisibleRootItem()
        for i in range(item.childCount()):
            item.child(i).setHidden(False)
        t.setRootIndex(self.hoistStack.pop())
    #@+node:vitalije.20200503150843.1: *3* updateToolbarButtons
    def updateToolbarButtons(self):
        self.undoAction.setEnabled(self.c.canUndo())
        self.redoAction.setEnabled(self.c.canRedo())
        curr = self.tree.currentItem()
        self.hoistAction.setEnabled(bool(curr) and curr.childCount() > 0)
        self.dehoistAction.setEnabled(bool(self.hoistStack))
    #@+node:vitalije.20200503145354.1: *3* API
    # here are official API methods that are used by the controller
    # for now there are only two methods here
    # resetBody and resetHeadline. Niether of these two is really
    # necessary MyGUI could just as easy set body and headline to the
    # currently selected node, but it does it indirectly. When body is
    # changed by user, MyGUI calls c.updateBody and controller then sets
    # v.b to new value. Similarily when user edits headline, MyGUI calls
    # c.updateHeadline which then calls back MyGUI.resetHeadline.

    # by this indirection it is possible for controller to decide
    # whether to accept changes or not and to call registered
    # plugin hooks for these events.

    # There should be here also methods for setting user icons
    # and also for expanding and collapsing to levels, for
    # moving around outline (selectPrev, selectNext, selectParent,
    # selectFirstChild)... also for modifying outline.
    # for moving cursor and scrollbars in body...
    # I don't expect any of these methods to be hard to implement.
    #@+node:vitalije.20200503141521.1: *4* resetBody
    def resetBody(self, b):
        self.body.blockSignals(True)
        self.body.setPlainText(b)
        self.body.blockSignals(False)
    #@+node:vitalije.20200503145914.1: *4* resetHeadline
    def resetHeadline(self, h):
        curr = self.currentItem()
        oldh = curr.text(0)
        if oldh != h:
            curr.setText(0, h)
    #@+node:vitalije.20200503145425.1: *3* event handlers
    #@+node:vitalije.20200502142951.1: *4* select_item
    def select_item(self, newitem, olditem):
        v = newitem.data(0, 1024)
        # we can call here registered hooks
        # for: select1, select2,...events or let the
        # controller call them.
        #
        # If we want we can even revert selection
        # to the previously selected node
        # by using:
        #    QtCore.QTimer.singleShot(1, lambda:self.tree.setCurrentItem(olditem))
        #    return
        self.updateToolbarButtons()
        self.c.setCurrentNode(v)
    #@+node:vitalije.20200502142954.1: *4* body_changed
    def body_changed(self):
        # we can here call directly self.resetBody
        # but to give controller some power here
        # we just ask it to updateBody which in turn
        # will usually call back resetBody
        self.c.updateBody(self.body.toPlainText())
    #@+node:vitalije.20200502142959.1: *4* update_headline
    def update_headline(self, item, col):
        if col == 0:
            self.c.updateHeadline(item.text(0))
            # we could update v.h here but
            # let the c decide appropriate action
            # which usually will call back resetHeadline
    #@+node:vitalije.20200503145321.1: *3* outline modifications
    #@+node:vitalije.20200503145328.1: *4* make_undoable_move
    def make_undoable_move(self, oldparent, srcindex, newparent, dstindex):
        def domove():
            curr = move_treeitem(oldparent, srcindex, newparent, dstindex)
            self.tree.setCurrentItem(curr)
        def undomove():
            curr = move_treeitem(newparent, dstindex, oldparent, srcindex)
            self.tree.setCurrentItem(curr)
        domove()
        self.c.addUndo(undomove, domove)
    #@+node:vitalije.20200503145331.1: *4* move_node_up
    def move_node_up(self):
        t = self.tree
        curr = t.currentItem()
        oldparent = curr.parent() or t.invisibleRootItem()
        srcindex = oldparent.indexOfChild(curr)
        prev = t.itemAbove(curr) # this might be the parent if srcindex == 0
        prev2 = prev and t.itemAbove(prev) 
        if not prev:
            return # there is nothing before. Can't move up
        elif srcindex == 0 and prev2 and prev2 is not prev.parent():
            # prev2 is not the parent of prev, therefore prev2 is the last
            # child of our newparent. We are moving just after the prev2
            newparent = prev2.parent() or t.invisibleRootItem()
            dstindex = newparent.indexOfChild(prev2) + 1
        else:
            newparent = prev.parent() or t.invisibleRootItem()
            dstindex =  newparent.indexOfChild(prev)
        if is_move_allowed(oldparent.data(0, 1024), srcindex,
                           newparent.data(0, 1024), dstindex):
            self.make_undoable_move(oldparent, srcindex, newparent, dstindex)
    #@+node:vitalije.20200503164722.1: *4* move_node_left
    def move_node_left(self):
        t = self.tree
        curr = t.currentItem()
        oldparent = curr.parent()
        if not oldparent:
            # already top level node. Can't move left.
            return
        srcindex = oldparent.indexOfChild(curr)
        newparent = oldparent.parent() or t.invisibleRootItem()
        dstindex = newparent.indexOfChild(oldparent) + 1
        # moving left is always safe.
        # No cycles can be made by moving node left.
        self.make_undoable_move(oldparent, srcindex, newparent, dstindex)

    #@+node:vitalije.20200503165313.1: *4* move_node_right
    def move_node_right(self):
        t = self.tree
        curr = t.currentItem()
        oldparent = curr.parent() or t.invisibleRootItem()
        srcindex = oldparent.indexOfChild(curr)
        if srcindex == 0:
            # can't move right
            return
        newparent = oldparent.child(srcindex - 1)
        dstindex = newparent.childCount()
        if is_move_allowed(oldparent.data(0, 1024), srcindex,
                           newparent.data(0, 1024), dstindex):
            self.make_undoable_move(oldparent, srcindex, newparent, dstindex)
    #@+node:vitalije.20200503151525.1: *4* move_node_down
    def move_node_down(self):
        t = self.tree
        curr = t.currentItem()
        oldparent = curr.parent() or t.invisibleRootItem()
        srcindex = oldparent.indexOfChild(curr)
        after = item_after(t, curr)
        if after and after.childCount() > 0 and after.isExpanded():
            newparent = after
            dstindex = 0
        elif after:
            newparent = after.parent() or t.invisibleRootItem()
            dstindex = newparent.indexOfChild(after) + 1
        else:
            newparent = t.invisibleRootItem()
            dstindex = newparent.childCount()
        if newparent == oldparent:
            dstindex -= 1
        if is_move_allowed(oldparent.data(0, 1024), srcindex,
                           newparent.data(0, 1024), dstindex):
            self.make_undoable_move(oldparent, srcindex, newparent, dstindex)
    #@+node:vitalije.20200503173119.1: *4* promote
    def promote(self):
        '''Promotes children to siblings'''
        t = self.tree
        curr = t.currentItem()
        if curr.childCount() == 0:
            return
        newparent = curr.parent() or t.invisibleRootNode()
        dstindex = newparent.indexOfChild(curr) + 1
        oldparent = curr
        links = [(oldparent, i, newparent, dstindex)
                    for i in range(curr.childCount(), 0, -1)]
        def dopromote():
            for oldparent, srcindex, newparent, dstindex in links:
                move_treeitem(oldparent, srcindex-1, newparent, dstindex)
            t.setCurrentItem(oldparent)
        def undopromote():
            for oldparent, srcindex, newparent, dstindex in reversed(links):
                move_treeitem(newparent, dstindex, oldparent, srcindex-1)
            t.setCurrentItem(oldparent)
        dopromote()
        self.c.addUndo(undopromote, dopromote)
    #@+node:vitalije.20200503175440.1: *4* demote
    def demote(self):
        '''Turns all following siblings to children of current node'''
        t = self.tree
        curr = t.currentItem()
        oldparent = curr.parent() or t.invisibleRootNode()
        srcindex = oldparent.indexOfChild(curr) + 1
        newparent = curr
        dstindex = newparent.childCount()
        n = oldparent.childCount() - srcindex
        if n == 0:
            # there are no following siblings
            return
        links = [(oldparent, srcindex, newparent, dstindex + i)
                   for i in range(n)]
        def dodemote():
            for oldparent, srcindex, newparent, dstindex in links:
                move_treeitem(oldparent, srcindex, newparent, dstindex)
            t.setCurrentItem(newparent)
        def undodemote():
            for oldparent, srcindex, newparent, dstindex in reversed(links):
                move_treeitem(newparent, dstindex, oldparent, srcindex)
            t.setCurrentItem(newparent)
        dodemote()
        self.c.addUndo(undodemote, dodemote)
    #@+node:vitalije.20200503153529.1: *4* hide_node
    # this was used just to see what is it like when item is hidden
    # hoist/dehoist works similar as chapters in Leo
    # but to make same effect as in Leo hoist/dehoist it may be
    # necessary to hoist on parent and then hide all other siblings
    def hide_node(self):
        t = self.tree
        curr = t.currentItem()
        after = item_after(t, curr) or t.itemAbove(curr)
        if not after:
            return
        curr.setHidden(True)
        t.setCurrentItem(after)
    #@-others
#@+node:vitalije.20200503141908.1: ** utilities
#@+node:vitalije.20200503134536.1: *3* is_move_allowed
def is_move_allowed(oldparent, srcindex, newparent, dstindex):
    '''Returns False if move would create cycle in the outline'''
    child = oldparent.children[srcindex]
    def it(v):
        yield v
        for ch in v.children:
            yield from it(ch)
    return not any(x is newparent for x in it(child))

#@+node:vitalije.20200503140008.1: *3* move_treeitem
def move_treeitem(oldparent, srcindex, newparent, dstindex):
    '''Moves child item oldparent.child(srcindex) to the
       newparent at index dstindex.
       This function also relinks the underlying v-nodes.
    
       Returns moved item.
    '''

    # first let's deal with the items
    item = oldparent.takeChild(srcindex)
    newparent.insertChild(dstindex, item)

    # and now let's deal with the v node links
    par_v = oldparent.data(0, 1024)
    v = par_v.children[srcindex]
    del par_v.children[srcindex]
    v.parents.remove(par_v)
    newpar_v = newparent.data(0, 1024)
    newpar_v.children.insert(dstindex, v)
    v.parents.append(newpar_v)

    return item
#@+node:vitalije.20200503142637.1: *3* item_after
# For implementing basic outline modification commands
# I needed just this one utility function for finding
# the item after (like p.nodeAfterTree())
# other p selectors (back, next, threadNext, ...) can
# be implemented just as easy as this one.
# (In case controller needs to tell tree widget to select
#  programaticaly any of adjacent items)
def item_after(tree, item):
    paritem = item.parent() or tree.invisibleRootItem()
    i = paritem.indexOfChild(item)
    if i + 1 < paritem.childCount():
        return paritem.child(i+1)
    def it(v):
        yield 1
        for ch in v.children:
            yield from it(ch)
    n = sum(it(item.data(0, 1024)))
    twi = QtWidgets.QTreeWidgetItemIterator(item)
    twi += n
    return twi.value()
#@+node:vitalije.20200502103535.1: *3* draw_tree
def draw_tree(tree, root):
    def additem(par, parItem):
        for ch in par.children:
            item = QtWidgets.QTreeWidgetItem()
            item.setFlags(item.flags() |
                          Q.ItemIsEditable |
                          item.DontShowIndicatorWhenChildless)
            parItem.addChild(item)
            item.setText(0, ch.h)
            item.setData(0, 1024, ch)
            item.setExpanded(ch.isExpanded())
            additem(ch, item)
    ritem = tree.invisibleRootItem()
    ritem.setData(0, 1024, root)
    additem(root, ritem)
#@-others
if __name__ == '__main__':
    if len(sys.argv) > 1:
        fname = sys.argv[1]
    else:
        fname = '/opt/programi/leo/trunk/leo/core/LeoPyRef.db'
    c = DummyLeoController(fname)
    myapp = MyGUI(c)
    myapp.create_main_window()
    myapp.exec_()
#@-leo