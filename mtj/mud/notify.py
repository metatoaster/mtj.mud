# mtmud.mud - A Basic Mud library in Python
# Copyright (c) 2007 Tommy Yu
# This software is released under the GPLv3

import logging
from mtmud.config import *
from mtmud.MudActions import *

LOG = logging.getLogger("actions")


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


class MoveObjFromTo(MudAction):
    """\
    Ancestor class that moves caller from target to second.

    This means it's initiated by caller.

    Different from caller wanting to move target to second.
    """

    def setResponse(self): #, caller, target, others, caller_siblings):
        # check result
        if self.result:
            self.callerMsg = 'You move from %s to %s.' % (self.target, self.second)
            self.targetMsg = '%s leaves you.' % (self.caller)
            self.secondMsg = '%s enters you.' % (self.caller)
        else:
            self.callerMsg = 'You failed to move from %s to %s.' % (self.target, self.second)

    def action(self):
        if self.caller and self.target and self.second:
            # all present
            return self.target.move_obj_to(self.caller, self.second)


class MoveObjTo(MudAction):
    """\
    Ancestor class that moves caller from to second regardless where
    it is.

    This could cause inconsistent state if caller is in some place but
    does not recognize that some place as its parent.
    """

    #   self.result = self.action()
    #   # this calls setResponse and _send
    #   MudNotify.__call__(self)
    #   self.post_action()
 
    # XXX - replace the replaced setResponse with init
    def __init__(self, *args, **kwargs):
        MudAction.__init__(self, *args, **kwargs)
        self.second = self.caller._parent

    def setResponse(self): #, caller, target, others, caller_siblings):
        # check result
        if self.result:
            self.callerMsg = 'You move from %s to %s.' % (self.target, self.second)
            self.targetMsg = '%s enters you.' % (self.caller)
            self.secondMsg = '%s leaves you.' % (self.caller)
            self._target_children = True
            self.target_childrenMsg = '%s enters.'
        else:
            self.callerMsg = 'You failed to move from %s to %s.' % (self.target, self.second)

    def action(self):
        if self.caller and self.target:
            # all present
            return self.caller.move_to(self.target)


class Go(MoveObjTo):
    """\
    Go (direction)

    Looks for an exit in meta.
    """

    def setResponse(self): #, caller, target, others, caller_siblings):
        # message every siblings
        self._caller_siblings = True
        if self.result:
            self.caller_siblingsMsg = '%s leaves %s.' % (self.caller, self.trail)
            # XXX this needs to be set based on whether player has stealth
            self._target_children = True
            self.target_childrenMsg = '%s enters.' % (self.caller)
        else:
            if self.trail:
                self.callerMsg = 'There is no %s exit.' % (self.trail)
            else:
                self.callerMsg = 'Where do you want to go?'

    def preparation(self):
        links = self.caller._parent.get_links(self.trail)
        # rooms with multiple exits will need to implement hooks
        # XXX naive implementation
        exit_d = dict(links)
        if self.trail in exit_d:
            self.target = exit_d[self.trail]
            return True

    # XXX HACK action is done later
    # Need to implement caller_sibling before action happened

    def post_action(self):
        if self.caller and self.target:
            # all present
            result = self.caller.move_to(self.target)
            if result:
                Look(self.caller)()
            return result

    def action(self):
        self.result = True
        return True


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


class Emote(MudNotify):
    """\
    Usage: emote <message>

    The say command emotes <message> to everyone in the room.
    """

    def setResponse(self): #, caller, target, others, caller_siblings):
        # message every siblings
        self._caller_siblings = True
        if self.trail:
            self.callerMsg = '::: %s %s :::' % (self.caller, self.trail)
            self.caller_siblingsMsg = '::: %s %s :::' % (self.caller, self.trail)
        else:
            self.callerMsg = 'What do you want to emote?'


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

    def post_action(self):
        if self.condition:
            soul = self.caller.soul
            if soul:
                # only those with souls can really quit
                soul.quit()
                self.caller._parent.remove(self.caller)
        # reflect success/failure
        return True


class Login(MudAction):
    """\
    The Login action will log in a user (caller) into a room (target).
    """

    def setResponse(self): #, caller, target, others, caller_siblings):
        # message every siblings
        self._caller_siblings = True
        self.caller_siblingsMsg = '%s arrives into this world.' % (self.caller)
        self.callerMsg = 'You arrive into this world.'

    def action(self):
        return self.target.add(self.caller)

    def post_action(self):
        # doing a call directly here to "avoid" drawing the prompt.
        # also to "emulate" an atomic call.
        Look(self.caller)()
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
        exits = room.roomlinks
        if not exits:
            x.append('        There are no obvious exits.\r\n\r\n')
        else:
            # XXX implement not obvious exits
            x.append('        Obvious exits are %s.\r\n\r\n' %
                     ', '.join(exits))
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
