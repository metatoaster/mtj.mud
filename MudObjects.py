# mtmud.mud - A Basic Mud library in Python
# Copyright (c) 2007 Tommy Yu
# This software is released under the GPLv3

import logging
import traceback
from socket import error as SocketError
from collections import deque

from config import *
from MudActions import *
from notify import *

LOG = logging.getLogger("MudObjects")


class MudObject(object):
    """\
    The root object for the Mud.

    All objects that exists within the world (or even ones that could
    take advantage from inheriting this class) should inherit this.
    """

    def __init__(self, shortdesc=None, longdesc=None, *args, **kwargs):
        """\
        Parameters:
        shortdesc - One line description of the object.  Could have 
            different meaning in subclasses.
        longdesc - Multi-line description of the object.  Could have
            different meaning in subclasses, but usually this meaning
            will be used.
        """
        self.shortdesc = shortdesc if shortdesc else type(self).__name__
        self.longdesc = longdesc

        # commands for this object (should only used by self)
        self._cmds = {}
        # commands usable by siblings
        self._siblings_cmds = {}
        # commands usable by parent
        self._parent_cmds = {}
        # commands usable by children
        self._children_cmds = {}

        # identifiers are hints to others on what else can select this
        # object.
        self._id = []

        # attributes will be used by players (and mobs) to determine
        # their strengths, agility, or basically statistics of them.
        # rooms could have temperature and water level attributes.
        # rooms may have to somehow automatically extend whatever
        # attributes exported by the area they belong to
        self.attributes = {}

        # tags are what normally gets tacked onto objects, not sure
        # how exactly this will be implemented.
        self.tag = []

        self._children = []  # XXX - call this better?
        self._parent = None  # XXX - can we make this more... dynamic?
        self._hb = None  # heartbeat

    def __iter__(self):
        return self._children.__iter__()

    def __str__(self):
        return self.shortdesc

    def _get_children(self):
        result = []
        result.extend(self._children)
        return result

    children = property(fget=_get_children)

    def _get_siblings(self):
        if not self._parent:
            # XXX this consistent?
            # reason: no parent, none
            return None
        return self._parent.children

    siblings = property(fget=_get_siblings)

    def _parse_cmd(self, input):
        x = input.split(' ', 1)
        if len(x) > 1:
            return x
        else:
            return input, ''

    def process_cmd(self, input):
        """\
        This method will process the input and find the command to
        execute, and will attempt to call each init_obj.
        """

        __algo = """\
        This is what the algorithm should look like:

        - Parse command
        - Find which object has this command, and construct the proper
          object
        - Done?
        """
        # XXX - should checks like these be required?
        #if not self.valid_cmd(cmd):
        #    return None
        cmd, arg = self._parse_cmd(input)
        LOG.debug('%s.process_cmd [%s, %s]',
                  self.__repr__(), cmd.__repr__(), arg.__repr__())

        if not cmd:
            return None

        # XXX - Not sure what command model/hierarchy to use
        # This model is search for commands to act on
        cmd_self = ('self', self)
        cmd_parent = ('parent', self._parent)
        cmd_children = ('child', self.children)
        # XXX this would *include* self, potential side effect that
        # will allow self pushing self, for instance.  this may need
        # to be fixed by the method that offers sibling...
        cmd_siblings = ('sibling', self.siblings)

        valid = (cmd_self, cmd_parent, cmd_children, cmd_siblings)

        # FIXME - kill these breaks.
        for name, obj in valid:
            objs = obj
            if not type(obj) is list:
                objs = [obj]
            for target in objs:
                # this line will always execute because self is not None
                result = target.init_cmd(self, cmd, arg)
                if result:
                    LOG.debug('%s.process_cmd, cmd in %s %s',
                              self.__repr__(), name, target.__repr__())

                    break
            if result:
                break

        return result

    def init_cmd(self, caller, cmd, arg):
        """\
        This method will find the cmd from self._cmds (which must be
        a MudAction) and will construct it to action it.

        Ideally this should not be overridden, but objects that needs
        to trap input (for instance, login) have to do so for now.
        """
        LOG.debug('%s.init_cmd(%s, %s, %s)',
                  self.__repr__(), 
                  caller.__repr__(), 
                  cmd.__repr__(), 
                  arg.__repr__(),
                 )
        # find relationship of self to caller
        # note: finding it here because calling from caller, the
        # relationship cmds will be reversed 
        if self == caller:
            cmds = self._cmds
        elif self == caller._parent:
            """
            target = self
            if target is the parent of the caller
            self/target self.parent
            caller/self
            """
            cmds = self._parent_cmds
        elif self in caller.children:
            # implies self._parent == caller
            cmds = self._children_cmds
        elif self in caller.siblings:
            cmds = self._siblings_cmds

        if not cmd in cmds:
            return None

        aC = cmds[cmd]
        # XXX this a sufficient check for valid class type?
        # XXX this check fails on a reload
        if issubclass(aC, MudNotify):
            # XXX may need to parse the trail and construct the notify
              # with proper targets, etc.
            a = aC(self, trail=arg)
            return a
            # this is the old way
            #return a.call()
        else:
            raise TypeError('%s (%s) is not subclass of MudNotify' %\
                (aC, type(aC)))

    def send(self, msg):
        LOG.debug('%s received %s', self.__repr__(), msg.__repr__())

    # XXX - may not be desirable for default
    addNotify = ObjAddNotify
    def add(self, obj):
        # assume contents to be list
        if obj._parent is not None:
            # XXX - uh, how did this happen?
            LOG.warning('%s.add(obj=%s), obj already has parent %s.  Aborted.',
                    self.__repr__(), obj.__repr__(), obj._parent.__repr__())
            return False
        obj._parent = self
        self._children.append(obj)
        if self.addNotify:
            e = self.addNotify(caller=self, target=obj)
            e.call()
        return True

    # XXX - may not be desirable for default
    removeNotify = ObjRemoveNotify
    def remove(self, obj):
        result = False
        if obj not in self._children: 
            # invalid
            if obj._parent != self:
                LOG.debug('%s not in %s; cannot remove', 
                    obj.__repr__(), self.__repr__())
                return False
            else:
                LOG.warning('%s is not children of but claims %s as parent; '\
                    'setting %s parent to None', 
                    obj.__repr__(), self.__repr__(), obj.__repr__())
                obj._parent = None
                # may need to notify obj
                return True
        else:
            self._children.remove(obj)
            if obj._parent == self:
                # only unset object's parent if this item is the true
                # parent.
                obj._parent = None
                result = True
                # completed normal ideal condition
            else:
                if obj._parent == None:
                    LOG.debug('%s did not have a parent to remove.', 
                        obj.__repr__())
                    result = True
                    # this condition is still fine
                else:
                    LOG.warning('%s was a children of %s but claims %s as parent.',
                    obj.__repr__(), self.__repr__(), obj._parent.__repr__())
                # notification
                return False
        # else FIXME put warning
        if self.removeNotify:
            e = self.removeNotify(caller=self, target=obj)
            e.call()
        return True

    def move_to(self, obj, target):
        # FIXME - this is not atomic operation
        # remove could do partial things...
        if self.remove(obj):
            return target.add(obj)
        return False

    def find_id(self, id_):
        """\
        Finds the object by the id supplied.

        Parameters:
        id_ - the string identifier to look for.
        """
        for i in self._children:
            if id_ in i.id:
                return i
        return None

    def _get_id(self):
        """\
        Returns a list of identifiers.
        """
        result = []
        result.append(self.shortdesc)
        result.extend(self._id)
        return result

    id = property(fget=_get_id)


class MudSprite(MudObject):
    """Anything that is somewhat smart?"""
    def __init__(self, soul=None, *args, **kwargs):
        self._soul = soul
        MudObject.__init__(self, *args, **kwargs)

    def send(self, msg):
        if self.soul and type(self.soul) is Soul:
            self.soul.send(msg)

    def _set_soul(self, soul):
        self._soul = soul

    def _get_soul(self):
        if self._soul and not self._soul.online:
            # assume to be dead
            LOG.debug('%s of %s is offline, removing reference',
                    self._soul.__repr__(), self.__repr__())
            self._soul = None
        return self._soul

    soul = property(
        fget=_get_soul,
        fset=_set_soul,
    )


class MudPlayer(MudSprite):
    room = property(fget=lambda self: self._parent)
    inventory = property(fget=lambda self: self._children)

    def __init__(self, name='Guest', *args, **kwargs):
        MudSprite.__init__(self, *args, **kwargs)
        self._other_souls = []  # XXX - ???
        self.shortdesc = name  # have to be regenerated on title change
        self.name = name
        # titles look like 'Duke %s, the Brave', with %s replaced by
        # player's name
        self.title = ''
        self._cmds = {
            'look': Look,
            'say': Say,
            'quit': Quit,
            'history': History,
            'help': Help,
        }  # dictionary of special commands

    def _full_name(self):
        if '%s' in self.title:
            try:
                result = self.title % self.shortdesc
            except:
                # XXX warn?
                result = self.shortdesc
        else:
            result = self.shortdesc
        return result
    
    full_name = property(fget=_full_name)
    __str__ = _full_name


class MudWizard(MudPlayer):
    # XXX placeholder class?
    def __init__(self, name='Wizard', *args, **kwargs):
        MudPlayer.__init(self, name, *args, **kwargs)
        self._cmds['create'] = Create


class MudArea(MudObject):
    def __init__(self, *args, **kwargs):
        # generic mudarea
        MudObject.__init__(self, *args, **kwargs)


class MudRoom(MudArea):
    def __init__(self, shortdesc='Empty Room', *args, **kwargs):
        # generic mudroom
        MudObject.__init__(self, shortdesc=shortdesc, *args, **kwargs)
        self.exits = {}


class MudExit(MudObject):
    available_barrier = [None, 'door', 'gate', 'portal',]

    def __init__(self, shortdesc='exit', *args, **kwargs):
        # generic exit
        MudObject.__init__(self, shortdesc=shortdesc, *args, **kwargs)
        self.barrier = None
        self.exits = {}
        #self.exits = {
        #    'north': NorthRoom,
        #    'south': SouthRoom,
        #}


class SoulGateKeeper(MudObject):
    # FIXME - should also inherit from special subclass

    def __init__(self, soul=None, *args, **kwargs):
        # self.soul = self._parent
        MudObject.__init__(self, *args, **kwargs)
        self.longdesc = 'Welcome to the MUD.\r\n'
        self.soul = soul
        self.login = None
        self.name = 'Unknown'  # XXX - workaround
        self.password = None

    def enter(self, soul):
        # XXX - why do we want a soul here?
        result = ''.join([self.longdesc, LOGIN_PROMPT])
        return result

    def valid_cmd(self, cmd):
        return True

    def init_cmd(self, caller, cmd, arg):
        """\
        Overrides the default, as it needs to have exclusive control.
        """
        # these sends directly to souls here are probably bad practice
        if type(cmd) is list:
            # XXX - like no error checking...
            cmd = cmd[0]
        if cmd:
            if not self.login:
                self.login = cmd
                # XXX - lol hacks and raw sends
                self.soul.request.send(PASSWORD_PROMPT)
            elif not self.password:
                self.password = cmd
        if self.login and self.password:
            # do login
            self.soul.send('')
            self.soul.send('You logged in as %s.' % (self.login))
            self.soul.send('This world is still work in progress, thus no actions by your character is permanent.')
            # XXX - load the body the user originally created.
            # FIXME - problem lines here, it's supposed to be a link
            # of some sort.
            body = MudPlayer(name=self.login, soul=self.soul)
            self.soul._parent = body
            # FIXME - um, use the queue to move player into room?
            room = self.soul.driver.starting['main']
            room.add(body)
            body._parent = room
            # XXX hackish to trick a look
            self.soul.driver.Q(Look(self.soul._parent), self.soul)
            #self.soul.body.room = MudObject()
        return True


class Soul(MudObject):
    """The soul of the connection, takes the request object from a
    connection, which connects to the user.

    This object could inherit from MudRunner and replace what 
    MudThread does.
    """
    # Would be nice if this is a body transfer technique
    def set_body(self, body): self._parent = body
    body = property(
        fget=lambda self: self._parent,
        fset=set_body,
    )
    logged_in = property(fget=lambda self: type(self.body) != SoulGateKeeper)

    def __init__(self, handler=None, *args, **kwargs):
        # XXX - may not be too smart about giving a user control object
        # all these references to resources above it?
        # XXX - even though the handler isn't the root object, it must
        # be used due to the scope of where this object was created.
        MudObject.__init__(self, *args, **kwargs)
        self.handler = handler
        self.request = handler.request
        self.server = handler.server
        self.controller = handler.server.controller
        self.driver = handler.server.controller.driver

        self.cmd_history = deque()
        self.cmd_offset = 1
        self.bad_count = 0
        self.online = None

        self.settings = {
          'max_history': 30,
        }

        # keep tracks of incoming rawdata
        self.rawq = []

        # the bodies
        self._parent = SoulGateKeeper(soul=self)
        # no () at the end so not to call it now
        # This may interfere with creating accounts with these names
        self._cmds = {
        }

    # communication
    def recv(self):
        # TODO - this can be made more efficient
        validChar = lambda x: 32 <= ord(x) <= 126
        ctrlChar = lambda x: ord(x) >= 240 or ord(x) < 32
        data = ''
        rawq = self.rawq
        while self.online and CHAR_TERM not in data:
            try:
                data = self.request.recv(MAX_DATA_LEN)
                LOG.log(0, 'received data (%02d|%s)' % 
                        (len(data), data.__repr__()))
                if not data:
                    self.online = False
                if data: # and validChar(data):
                    rawq.append(data)
            except:
                # something real bad must have happened, forcing 
                # offline to be safe
                self.online = False
                raise

        # do error validation here.
        # else:
        #     LOG.debug('Last chunk too long, scanning for next newline')
        #     self.bad_count += 1
        # if self.bad_count > MAX_BAD:
        #     LOG.debug('bad_count maxxed out, dropping connection')
        #     return

        # fresh queue after we grabbed output
        raw = ''.join(rawq)
        LOG.debug('Received raw data: %s', raw.__repr__())
        rawq = []

        # FIXME - put this in better place
        # look for telnet nvt codes and handle them.
        iac = '\xff\xfd\x06'
        iac_c = 0

        lines = []  # all the good lines
        line = []   # current line (chars)
        for c in raw:
            if validChar(c):
                line.append(c)
            if ctrlChar(c):
                # XXX hack for ctrl-c handling sent from telnet
                if iac[iac_c] == c:
                    iac_c += 1
                else:
                    iac_c = 0

                if iac_c == 3:
                    LOG.debug('acting on iac')
                    iac_c = 0
                    self.request.send('\xff\xfb\x06')
            if c in CMD_TERM:
                # XXX only send prompt on carriage return
                if line or (not line and c == CHAR_TERM):
                    lines.append(''.join(line))
                    line = []
        if line:
            # append leftovers for next round...
            rawq.append(''.join(line))
        self.rawq = rawq
        LOG.debug('got lines: %s', str(lines))

        return lines

    def send(self, msg, newline=True):
        if not self.online:
            LOG.warning('%s is offline: cannot send %s.',
                        self.__repr__(),
                        msg.__repr__(),
                        )
            return False
        try:
            LOG.debug('sending msg: %s', msg.__repr__())
            # XXX - maybe abstract these telnet codes away, or use the
            # telnet class?
            self.request.send('\xff\xfb\x01%s' % msg)
            if newline:
                # don't send dup newlines
                if msg.__str__()[-2:] != '\r\n':
                    self.request.send('\r\n')
            # reset of some sort for a new line
            self.request.send('\xff\xfc\x01')
            return True
        except:
            LOG.warning('cannot send message to %s', self.__repr__())
            LOG.warning('message was: %s', msg.__repr__())

    def loop(self):
        if self.online == None:
            self.online = True
            self.send(self.server.greeting_msg, False)

        while self.online:
            try:
                lines = self.recv()
                LOG.debug('%s command count = (%d)',
                        str(self.handler.client_address), len(lines))
                for data in lines:
                    LOG.debug('processing data')
                    # handle command parsing here
                    self.bad_count = 0
                    cmd = data.strip()
                    if cmd:
                        LOG.debug('%s cmd: %s',
                                  str(self.handler.client_address), 
                                  cmd.__repr__(),
                                 )
                        self.rec_history(data)
                    # send to queue
                    a = self.body.process_cmd(cmd)
                    logging.debug('process_cmd returns: %s', a.__repr__())
                    if isinstance(a, MudNotify):
                        self.driver.Q(a, self)
                    elif a == True:
                        # it means this command was handled somewhere.
                        pass
                    elif data:
                        # command not handled; notify user
                        #self.send('%s not a valid command, please try again!' %
                        #    cmd.__repr__())
                        self.send('Please try again!')
                        self.prompt()
                    else:
                        # blank command, send prompt
                        self.prompt()

            except SocketError:
                # XXX handling different codes may be nice
                LOG.debug('%s got a socket error, terminating connection.',
                          self.__repr__())
                self.online = False
            except:
                LOG.warning('%s got an exception!', self.__repr__())
                LOG.warning(traceback.format_exc())
                self.send('A serious error has occurred!')
        LOG.debug('%s is offline, terminating connection.', str(self))

    def handle(self):
        try:
            self.loop()
        except:
            # wow, something messed up bad.
            # currently the login process is _outside_ the exception
            # block, so if login craps out this will definitely be
            # thrown.
            LOG.error('%s exception has leaked out of loop!',
                    self.__repr__())
            LOG.error(traceback.format_exc())
            self.send('A critical error has occured!')
            self.send('You have been disconnected!')

    # support
    def process_cmd(self, *args, **kwargs):
        result = MudObject.process_cmd(self, *args, **kwargs)
        # XXX this should be generalized to find out if _parent offers
        # a prompt
        if type(self._parent) != SoulGateKeeper:
            self.prompt()
        return result

    def prompt(self):
        if self.online:
            self.request.send('\xff\xfd\x01')
            self.request.send(STD_PROMPT)

    def greeting(self):
        LOG.debug('created soul %s', self)
        self.send('hi %s' % str(self.handler.client_address))

    def history(self):
        # XXX - the list cmd sending requires cmd param...
        result = []
        for h in enumerate(self.cmd_history):
            result.append(' %4d  %s' % (h[0] + self.cmd_offset, h[1]))
        return '\r\n'.join(result)

    def quit(self):
        # XXX - the list cmd sending requires cmd param...
        self.send('Goodbye %s, see you soon.' % str(self.body.name))
        self.online = False
        return True

    def rec_history(self, cmd):
        if not self.logged_in:
            return None
        self.cmd_history.append(cmd)
        if len(self.cmd_history) > self.settings['max_history']:
            self.cmd_offset += 1
            self.cmd_history.popleft()


class ChatChannel(MudObject):
    """Chat channel.
    """
    # FIXME - MudObject
    def __init__(self, *args, **kwargs):
        # change children to set()?
        # FIXME - should be links to bodies.
        self.souls = set()  # maybe don't call them souls here?

    def join(self, soul):
        # XXX - type checking
        # also existing check?
        self.souls.add(soul)

    def leave(self, soul):
        """Leaves this chat channel."""
        if soul in souls:
            self.souls.remove(soul)
            return True
        else:
            return False

    def send(self, sender, msg):
        # sanity checks here
        for s in souls:
            m = '%s [%s] %s' % (sender, self.name, msg)
            s.send(m)

