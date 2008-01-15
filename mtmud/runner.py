# mtmud.mud - A Basic Mud library in Python
# Copyright (c) 2007 Tommy Yu
# This software is released under the GPLv3

import socket
from collections import deque
import logging
import traceback
import threading
import time

from config import *
from server import *
from MudObjects import *
from MudActions import *
from world import *

LOG = logging.getLogger("runner")


class MudRunner(MudObject):
    """\
    Ancestor thread runner class.  Anything that needs to run for a
    while in a different thread should inherit this.
    """

    def __init__(self, *args, **kwargs):
        """\
        Initialize some runner
        """
        MudObject.__init__(self, *args, **kwargs)
        self._running = False
        self.t = None  # the thread

    def _begin(self):
        """\
        Redefine to set up what should be done.
        """
        pass

    def _action(self):
        """\
        Redefine to set up what should be done.
        """
        pass

    def _end(self):
        """\
        Redefine to set up what should be done.
        """
        pass

    def _run(self):
        while self._running:
            self._action()

    def _start(self):
        """\
        The dummy start method that is called by the actual start
        method, which will run this method in a separate thread.
        """
        self._begin()
        self._running = True
        try:
            self._run()
        finally:
            if self._running:
                # FIXME - this does not call thread join
                self._end()

    def start(self):
        """Spawns a new thread that will run the code defined in _run."""
        self.t = threading.Thread(target = self._start)
        self.t.start()

    def stop(self):
        """Terminates server."""
        try:
            self._end()
        except:
            self._running = False
            raise
        # Join the thread
        self._running = False
        self.t.join(5)
        self.t.isAlive()

    def isRunning(self):
        return self._running


class MudServerController(MudRunner):
    """\
    The server controller.

    An instance of this class will spawn a server on a separate thread
    that will listen on HOST:PORT once its start method is called.
    """

    listenAddr = property(lambda self: (self.host, self.port))
    driver = property(lambda self: self._parent)

    def __init__(self, host, port, *args, **kwargs):
        """\
        Initializes the controller, set constants from config file, etc.
        
        Currently does nothing too important for now.
        """
        # parent is the driver
        MudRunner.__init__(self, *args, **kwargs)
        self.server = None
        self.chats = {}
        self.chats['global'] = ChatChannel()
        self.host = host
        self.port = port

    def _begin(self):
        if self._running:
            LOG.warn('Server %s already started.' % self.server)
            return
        try:
            LOG.info('Starting server...')
            self.server = ThreadingMudServer(
                    self.listenAddr, MudRequestHandler, self)
            LOG.info('Started server %s', self.server)
        except socket.error:
            LOG.warn('Failed to start server %s', self.server)
            raise

    def _action(self):
        self.server.handle_request()

    def _end(self):
        if self.server and self._running:
            # XXX - needed here, server_close could toss exception
            LOG.info('Shutting down server %s.', self.server)
            self.server.server_close()
        else:
            LOG.debug('No running server to stop.')


class MudDriver(MudRunner):
    """\
    The mud driver.
    
    This is what drives all actions in the mud, or where main events
    spawned by objects of the world should execute in.
    """
    nexthb = property(fget=lambda self: self.lasthb + self.hbdelay)
    areas = property(fget=lambda self: self._children)

    def __init__(self, *args, **kwargs):
        # children are servers serving this world
        MudRunner.__init__(self, *args, **kwargs)
        self.starting = {}
        self.cmdQ = deque()
        self.counter = 0
        self.time = 0
        self.lasthb = 0  # every timeout

        # XXX magic number here
        self.timeout = 0.002  # seconds, default 2 millisecond
        self.hbdelay = 2  # seconds

        self._build_world()

    def _begin(self):
        pass

    def _action(self):
        while self.cmdQ:
            # nobody else is popping this list, so when this is true
            # there must be an item to pop.  No false positives either
            # as append is atomic.
            cmd = self.cmdQ.popleft()
            # FIXME
            LOG.debug('cmdQ -> (%s)', cmd.__repr__())
            try:
                cmd()
                # XXX prompt
                if isinstance(cmd.sender, Soul):
                    cmd.sender.prompt()
            except:
                LOG.warning(
                    "command '%s' caused an exception", cmd.__repr__())
                LOG.warning(traceback.format_exc())
                if cmd.sender:
                    cmd.sender.send('A serious error has occurred!')
            # parse cmd
        self.counter += 1
        self.time = time.time()
        if self.time >= self.nexthb:
            self.lasthb = self.time
            LOG.log(1, 'heartbeat @ %f', self.lasthb)
            # do checks and heartbeats here.
        # all done, go sleep for a bit.
        time.sleep(self.timeout)

    def _end(self):
        # save the world!
        pass

    def _build_world(self):
        # builds the world
        self.add(Foundation())
        self.starting = {
            'main': self._children[0]._children[0],
        }

    def Q(self, cmd, sender=None):
        """\
        Queue a command.  Commands are just strings.
        """
        LOG.debug('cmdQ <- (%s, %s)', sender.__repr__(), cmd.__repr__())
        if sender:
            cmd.sender = sender
        self.cmdQ.append(cmd)
        # this is an atomic operation.

