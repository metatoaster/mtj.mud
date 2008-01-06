# mtmud.mud - A Basic Mud library in Python
# Copyright (c) 2007 Tommy Yu
# This software is released under the GPLv3

import logging
from config import *

LOG = logging.getLogger("MudActions")


class MudNotify(object):
    """\
    Ancestor class to encapsulate notification routines.

    This class is instantiated to send a message to related MudObjects
    using their send method.  It's up to the targeted class on what to
    do to the message(s) they receive.
    """

    def __init__(
            self, 
            caller,
            target=None,
            second=None, 
            caller_siblings=None, 
            caller_children=None,
            target_siblings=None, 
            target_children=None,
            trail=None,
        ):
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
        self._caller_siblings = caller_siblings
        self._caller_children = caller_children
        self._target_siblings = target_siblings
        self._target_children = target_children

        # default outputs
        self.callerMsg = None
        self.targetMsg = None
        self.secondMsg = None
        self.caller_siblingsMsg = None
        self.caller_childrenMsg = None
        self.target_siblingsMsg = None
        self.target_childrenMsg = None

        self.setResponse()

    def _get_clean_children(self, param, obj, rem=None):
        """\
        Using param (one of the related self._ variables) to determine
        a list of chosen children, with the list cleaned of caller,
        target, and second target.

        The removal behavior may have to be changed later.

        Also, this method may need to be unified with MudObject
        """
        result = []
        LOG.debug('clean children (%s, %s)', param.__repr__(), obj.__repr__())
        if param is True:
            if obj:
                result = obj.children
                # remove extras.
                if type(rem) not in (list, set):
                    rem = set([self.caller, self.target, self.second])
                # XXX smarter way to deal with this nested
                for r in rem:
                    if r in result:
                        result.remove(r)
        elif type(param) is list:
            result = param
        return result

    def _get__caller_children(self):
        return self._get_clean_children(
                self._caller_children, self.caller)
    caller_children = property(fget=_get__caller_children)

    def _get__caller_siblings(self):
        return self._get_clean_children(
                self._caller_siblings, self.caller._parent)
    caller_siblings = property(fget=_get__caller_siblings)

    def _get__target_children(self):
        return self._get_clean_children(
                self._target_children, self.target)
    target_children = property(fget=_get__target_children)

    def _get__target_siblings(self):
        return self._get_clean_children(
                self._target_siblings, self.target._parent)
    target_siblings = property(fget=_get__target_siblings)

    def call(self):
        """\
        Call this method to send the message.

        This may be converted into a metaclass method?
        """
        LOG.debug('%s(%s)', self.__repr__(), self.caller.__repr__())
        self._send()
        # XXX always True?
        return True

    def _send(self):
        """\
        This method sends the output to each targets.
        """
        # XXX make this into a list to save lines
        if self.caller and self.callerMsg:
            self.caller.send(self.callerMsg)
        if self.target and self.targetMsg:
            self.target.send(self.targetMsg)
        if self.second and self.secondMsg:
            self.second.send(self.secondMsg)
        if self.caller_siblingsMsg:
            for cs in self.caller_siblings:
                cs.send(self.caller_siblingsMsg)
        if self.caller_childrenMsg:
            for cs in self.caller_children:
                cs.send(self.caller_childrenMsg)


    def setResponse(self): #, caller, target, others, caller_siblings):
        """\
        Redefine this method to set the output response for the 
        selected caller and targets.
        """


class MudAction(MudNotify):
    """\
    This class not only does what MudNotify can, but can also action
    something if the action method is redefined.
    """

    def call(self):
        """\
        Call this method to send the message and call action.

        This may be converted into a metaclass method?
        """
        LOG.debug('%s(%s)', self.__repr__(), self.caller.__repr__())
        # XXX check order
        self._send()
        result = self.action()
        return result

    def action(self):
        """\
        Redefine this method to process other actions that may need to
        happen before any output is sent.
        """
        return False


class MudNotifyDefault(MudNotify):
    """\
    An Example MudNotify implementation
    """

    def setResponse(self): #, caller, target, others, caller_siblings):
        """\
        Redefine this method to set the output response for the 
        selected caller and targets.
        """
        self.callerMsg = 'You action with %s on %s' % \
                (self.second, self.target)
        self.targetMsg = '%s does action with %s on you' % \
                (self.caller, self.second)
        self.secondMsg = '%s does action with you on %s' % \
                (self.caller, self.target)
        self.sibsMsg = '%s does action with %s on %s' % \
                (self.caller, self.second, self.target)


class MudActionMulti():
    """\
    Action class that accepts multiple selected targets.

    This is currently a placeholder class.
    """
    def __init__(self, caller, target=None, others=None, caller_siblings=None):
        """\
        Parameters:
        caller - the object that created this action
        target - the target object
        others - a list of secondary targetted object
        caller_siblings - specific list of caller siblings to message to.
            if True the siblings will be assumed to be children of the
            parent of the caller, if caller has parent.
            if a list of objects is specified, it's assumed they are
            chosen siblings of caller.
            else no siblings will be notified.
        """
        pass


class ObjAddNotify(MudNotify):
    """\
    Ancestor class that enables notification of siblings and object
    that got added.

    Perhaps turning this into an action class may be better.
    """

    def setResponse(self): #, caller, target, others, caller_siblings):
        self._caller_children = True
        self.callerMsg = '%s appears inside you.' % (self.target)
        self.targetMsg = 'You appear inside %s.' % (self.caller)
        self.caller_childrenMsg = '%s appears.' % (self.target)


class ObjRemoveNotify(MudNotify):
    """\
    Ancestor class that enables notification of siblings and object
    that got removed.

    Perhaps turning this into an action class may be better.
    """

    def setResponse(self): #, caller, target, others, caller_siblings):
        self._caller_children = True
        self.callerMsg = '%s vanishes from you.' % (self.target)
        self.targetMsg = 'You vanish from %s.' % (self.caller)
        self.caller_childrenMsg = '%s vanishes.' % (self.target)


class History(MudNotify):
    """\
    Usage: history

    This command shows you a history of the commands you have entered.
    """

    def setResponse(self): #, caller, target, others, caller_siblings):
        if hasattr(self.caller, 'soul'):
            self.callerMsg = self.caller.soul.history()


class Say(MudNotify):
    """\
    Usage: say <message>

    The say command sends <message> to everyone listening within the
    current room.
    """

    def setResponse(self): #, caller, target, others, caller_siblings):
        # message every siblings
        self._caller_siblings = True
        if self.trail:
            self.callerMsg = 'You say, "%s"' % (self.trail)
            self.caller_siblingsMsg = '%s says, "%s"' % (self.caller, self.trail)
        else:
            self.callerMsg = 'Keeping what you want to say to yourself is '\
                'detrimental to your health.'


class Quit(MudAction):
    """\
    Usage: quit

    This command will safely quit you out of this world, and hopefully
    returns you back into the real world.
    """

    def setResponse(self): #, caller, target, others, caller_siblings):
        # message every siblings
        self._caller_siblings = True
        self.condition = not self.trail
        if self.trail:
            self.callerMsg = 'Quit what?'
        else:
            # XXX don't message if quit didn't work
            self.caller_siblingsMsg = '%s has left this world.' % (self.caller)

    def action(self):
        if self.condition:
            soul = self.caller.soul
            if soul:
                # only those with souls can really quit
                soul.quit()
                self.caller._parent.remove(self.caller)
        # reflect success/failure
        return True
        

class Help(MudNotify):
    """\
    Usage: help <command>

    Calling 'help' alone will give you this page and a brief listing on
    what commands you have access to if called without any arguments.
    If a valid command you have access to is passed as an argument, the 
    help for that command will be presented to you.
    """
    # FIXME - need to subclass MudNotify to output pages of text
    # FIXME - eventually need some sort of automagical way to change
    # newlines to ones with return carriage for things that require it
    # XXX - Assuming caller to be a Soul.

    def setResponse(self):
        if self.trail:
            doc = None
            if self.trail in self.caller._cmds:
                doc = self.caller._cmds[self.trail].__doc__
            # XXX disabling soul/body...
            # elif self.trail in self.caller.body._cmds:
            #     doc = self.caller.body._cmds[self.trail].__doc__

            if doc and doc != '':
                self.callerMsg = doc.replace('\n', '\r\n')
            else:
                self.callerMsg = 'There is no help available on that topic.'
        else:
            self.callerMsg = self.__doc__.replace('\n', '\r\n')
            f = ['\r\n    Valid commands are:']
            for c in self.caller._cmds:
                f.append('      - %s' % c)
            # for c in self.caller.body._cmds:
            #     f.append('      - %s' % c)
            self.callerMsg += '\r\n'.join(f)


class _Look():

    def _look(self, room, contents):
        x = []
        x.append('%s\r\n\r\n%s\r\n' % (room.shortdesc, room.longdesc))
        # if type(room):
        x.append('        There are no obvious exits.\r\n\r\n')
        for c in contents:
            x.append(' %s\r\n' % c)
        return ''.join(x)

    def _lookitem(self, room, contents):
        x = []
        x.append('%s\r\n\r\n%s\r\n' % (room.shortdesc, room.longdesc))
        for c in contents:
            x.append(' %s\r\n' % c)
        return ''.join(x)


class Look(MudNotify, _Look):
    """\
    Usage: look [<item>]

    One of the most important commands you will ever use, look will
    allow you to inspect your surroundings and items you specify that
    are in your surroundings or your inventory.
    
    Status: Under development.  Items do not work.
    """

    # this look is a look from the children wanting to see their
    # parent and surroundings (i.e. caller's siblings)

    def setResponse(self): #, caller, target, others, caller_siblings):
        # setting this to true to enable building of the sibling list
        self._caller_siblings = True
        room = self.caller._parent
        if room:
            template = self._look(room, self.caller_siblings)
            self.callerMsg = template
        else:
            self.callerMsg = "You are not in a room!"


class LookFromTarget(MudNotify, _Look):
    """\
    Using target to look, as if caller using target's eyes to look.
    
    Status: Under development.  Items do not work.
    """

    # this look is a look from the children wanting to see their
    # parent and surroundings (i.e. caller's siblings)


    def _get__target_siblings(self):
        rem = set([self.target, self.second])
        return self._get_clean_children(
                self._target_siblings, self.target._parent, rem)
    target_siblings = property(fget=_get__target_siblings)

    def setResponse(self): #, caller, target, others, caller_siblings):
        # setting this to true to enable building of the sibling list
        self._target_siblings = True
        room = self.target._parent
        if room:
            template = self._look(room, self.target_siblings)
            self.callerMsg = template
        else:
            self.callerMsg = "You are not in a room!"


class LookFromRoom(MudNotify, _Look):
    """\
    If the rooms can look, it will do this.
    
    target would be the target to send the result to.
    
    Status: Under development.  Items do not work.
    Notes: This is from the perspective of the room.
    """

    # FIXME inherit this template from somewhere.
    def setResponse(self): #, caller, target, others, caller_siblings):
        # setting True to build the list.
        self._caller_children = True
        room = self.caller
        template = self._look(room, self.caller_children)
        self.targetMsg = template  # implies target needed.
