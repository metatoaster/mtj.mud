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
            sender=None,
            *args,
            **kwargs
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

        self.sender = sender
        if self.sender is None:
            # default should be whoever constructed this object
            pass

        # default outputs
        self.callerMsg = None
        self.targetMsg = None
        self.secondMsg = None
        self.caller_siblingsMsg = None
        self.caller_childrenMsg = None
        self.target_siblingsMsg = None
        self.target_childrenMsg = None

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

    def __call__(self):
        """\
        Call this method to send the message.
        """
        LOG.debug('%s(%s)', self.__repr__(), self.caller.__repr__())
        self.setResponse()
        self._send()
        # XXX always True?
        return True

    def __repr__(self):
        s = '<%s.%s object, sender %s>' % (
            self.__class__.__module__,
            self.__class__.__name__,
            self.sender.__repr__(),
        )
        return s

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

    def __call__(self):
        """\
        Call this method to send the message and call action.

        This may be converted into a metaclass method?
        """
        self.result = self.action()
        MudNotify.__call__(self)
        self.post_action()
        # XXX what kind of result code to return?
        return self.result

    def action(self):
        """\
        Redefine this method to process other actions that may need to
        happen before any output is sent.
        """
        return False

    def post_action(self):
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


class MudPortal(MudAction):
    """\
    A portal.  Foundation class that encapsulates an exit.
    """
    # If this must be instantiated as an object (like, a portal), there
    # needs to be a subclass that inherits from this and MudObject

    # caller and target are interchangable.
    # needs input direction, for things like mislead

    _exit = '%s leaves %s.'
    _enter = '%s enters.'

    def __init__(self, *args, **kwargs):
        MudAction.__init__(self, *args, **kwargs)

    def __call__(self, user, direction, *args, **kwargs):
        #if user in self.caller:
        if user._parent == self.caller:
            # move from caller to target
            pass
        elif user._parent == self.target:
            # move from target to caller
            pass
