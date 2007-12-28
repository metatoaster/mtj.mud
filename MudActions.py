# mtmud.mud - A Basic Mud library in Python
# Copyright (c) 2007 Tommy Yu
# This software is released under the GPLv3

import sys
import socket
from collections import deque
from SocketServer import TCPServer, BaseRequestHandler
import logging
import traceback
import threading
import time
from config import *

LOG = logging.getLogger("MudActions")


class MudAction():
    """\
    Ancestor class to encapsulate an action.
    """
    def __init__(self, trail, caller, target=None, second=None, caller_sibs=None):
        """\
        Parameters:
        trail - the trailing text of the command that was sent.
            * this may be redefined to require the parse tuple to be
              sent.
        caller - the object that created this action
        target - the target object
        second - the secondary selected target
        caller_sibs - specific list of caller siblings to message to.
            if True the siblings will be assumed to be children of the
            parent of the caller, if caller has parent.
            if a list of objects is specified, it's assumed they are
            chosen siblings of caller.
            else no siblings will be notified.
        """
        self.trail = trail
        self.caller = caller
        self.target = target
        self.second = second
        self.caller_sibs = []
        if caller_sibs is True:
            if caller._parent:
                self.caller_sibs.extend(caller._parent._children)
                # XXX remove caller and target(s) like so, sane?
                if caller in self.caller_sibs: self.caller_sibs.remove(caller)
                if target in self.caller_sibs: self.caller_sibs.remove(target)
                if second in self.caller_sibs: self.caller_sibs.remove(second)
        elif type(caller_sibs) is list:
            self.caller_sibs = caller_sibs

        # default outputs
        self.callerMsg = None
        self.targetMsg = None
        self.secondMsg = None
        self.sibsMsg = None

        self.setResponse()

    def call(self):
        """\
        Call this method to commit the action.

        This may be converted into a metaclass?
        """
        self.action()
        self._send()

    def _send(self):
        """\
        This method sends the output to each targets.
        """
        if self.caller and self.callerMsg:
            self.caller.send(self.callerMsg)
        if self.target and self.targetMsg:
            self.target.send(self.targetMsg)
        if self.second and self.secondMsg:
            self.second.send(self.secondMsg)
        if self.sibsMsg:
            for cs in self.caller_sibs:
                cs.send(self.sibsMsg)


    def setResponse(self): #, caller, target, others, caller_sibs):
        """\
        Redefine this method to set the output response for the 
        selected caller and targets.
        """

    def action(self):
        """\
        Redefine this method to process other actions that may need to
        happen before any output is sent.
        """


class MudActionDefault(MudAction):
    """\
    An Example MudAction class.
    """

    def setResponse(self): #, caller, target, others, caller_sibs):
        """\
        Redefine this method to set the output response for the 
        selected caller and targets.
        """
        self.callerMsg = 'You do MudAction with %s on %s' % \
                (self.second, self.target)
        self.targetMsg = '%s does MudAction with %s on you' % \
                (self.caller, self.second)
        self.secondMsg = '%s does MudAction with you on %s' % \
                (self.caller, self.target)
        self.sibsMsg = '%s does MudAction with %s on %s' % \
                (self.caller, self.second, self.target)


class MudActionMulti():
    """\
    Action class that accepts multiple selected targets.

    This is currently a placeholder class.
    """
    def __init__(self, caller, target=None, others=None, caller_sibs=None):
        """\
        Parameters:
        caller - the object that created this action
        target - the target object
        others - a list of secondary targetted object
        caller_sibs - specific list of caller siblings to message to.
            if True the siblings will be assumed to be children of the
            parent of the caller, if caller has parent.
            if a list of objects is specified, it's assumed they are
            chosen siblings of caller.
            else no siblings will be notified.
        """
        pass


class Say(MudAction):
    """\
    Usage: say <message>

    The say command sends <message> to everyone listening within the
    current room.
    """

    def __init__(self, trail, caller, target=None, second=None, caller_sibs=None):
        MudAction.__init__(self, trail, caller, target, second, caller_sibs=True)

    def setResponse(self): #, caller, target, others, caller_sibs):
        if self.trail:
            self.callerMsg = 'You say, "%s"' % (self.trail)
            self.sibsMsg = '%s says, "%s"' % (self.caller, self.trail)
        else:
            self.callerMsg = 'Saying nothing is no good.'


class Look(MudAction):
    """\
    Usage: look [<item>]

    One of the most important commands you will ever use, look will
    allow you to inspect your surroundings and items you specify that
    are in your surroundings or your inventory.
    
    Status: Under development.  Items do not work.
    """

    def __init__(self, trail, caller, target=None, second=None, caller_sibs=None):
        # cheat to build the list of caller_sibs... this will need
        # to be fixed for more versatility
        MudAction.__init__(self, trail, caller, target, second, caller_sibs=True)

    _look_sample = """\
        Example output might be something like:

        Empty Room

        This is a very empty room.
                There are no obvious exits.

         Player
         Guest
         Somebody

        """

    def setResponse(self): #, caller, target, others, caller_sibs):
        room = self.caller._parent
        if room:
            template = '%s\r\n\r\n%s\r\n' % (room.shortdesc, room.longdesc)
            template += '        There are no obvious exits.\r\n\r\n'
            for sib in self.caller_sibs:
                template += ' %s\r\n' % sib
            self.callerMsg = template
        else:
            self.callerMsg = "You are not in a room!"

