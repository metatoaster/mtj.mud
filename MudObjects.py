# mtmud.mud - A Basic Mud library in Python
# Copyright (c) 2007 Tommy Yu
# This software is released under the GPLv3

import logging
import traceback

from config import *
from MudActions import *

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
        self.cmds = {}
        # commands usable by siblings
        self.sibling_cmds = {}
        # commands usable by parent
        self.parent_cmds = {}
        # commands usable by children
        self.children_cmds = {}

        # attributes will be used by players (and mobs) to determine
        # their strengths, agility, or basically statistics of them.
        # rooms could have temperature and water level attributes.
        # rooms may have to somehow automatically extend whatever
        # attributes exported by the area they belong to
        self.attributes = {}

        self._children = []  # XXX - call this better?
        self._parent = None  # XXX - can we make this more... dynamic?
        self._hb = None  # heartbeat

    def __str__(self):
        return self.shortdesc

    def _parse_cmd(self, input):
        x = input.split(' ', 1)
        if len(x) > 1:
            return x
        else:
            return input, ''

    def process_cmd(self, input):
        # XXX - should checks like these be required?
        #if not self.valid_cmd(cmd):
        #    return None
        cmd, arg = self._parse_cmd(input)

        # XXX - Not sure what command model/hierarchy to use
        # This model is search for commands to act on
        LOG.debug('%s.process_cmd [%s, %s]' % \
                (self.__repr__(), cmd.__repr__(), arg.__repr__()))
        if self.valid_cmd(cmd):
            LOG.debug('%s.process_cmd, cmd in self' % (self.__repr__()))
            result = self.do_cmd(self, cmd, arg)
            #selfMsg, targetMsg, othersMsg = self.cmds[cmd](msg)
        elif self._parent and self._parent.valid_cmd(cmd):
            LOG.debug('%s.process_cmd, cmd in parent %s' % 
                    (self.__repr__(), self._parent.__repr__()))
            result = self._parent.do_cmd(self, cmd, arg)
            #selfMsg, targetMsg, othersMsg = self._parent.cmds[cmd](msg)
        else:
            # search children
            for child in self._children: 
                if child.valid_cmd(cmd):
                    LOG.debug('%s.process_cmd, cmd in children %s' %
                            (self.__repr__(), child.__repr__()))
                    result = child.do_cmd(self, cmd, arg)
                    #selfMsg, targetMsg, othersMsg = child.cmds[cmd](msg)
                    break

            # search siblings
            # XXX child = sibling here
            siblings = []
            if self._parent:
                siblings = self._parent._children
            for child in siblings:
                if child.valid_cmd(cmd):
                    LOG.debug('%s.process_cmd, cmd in sibling %s' %
                            (self.__repr__(), child.__repr__()))
                    result = child.do_cmd(self, cmd, arg)
                    #selfMsg, targetMsg, othersMsg = child.cmds[cmd](msg)
                    break

    def valid_cmd(self, cmd):
        return cmd in self.cmds

    def do_cmd(self, caller, cmd, arg):
        # FIXME - this is NOT what I designed.
        LOG.debug('%s.do_cmd(%s, %s, %s)' % \
                (self.__repr__(), 
                    caller.__repr__(), 
                    cmd.__repr__(), 
                    arg.__repr__()
                ))
        aC = self.cmds[cmd]
        if type(aC).__name__ == 'classobj' and issubclass(aC, MudAction):
            # FIXME get support of the other variables into here.
            # (self, trail, caller, target, second, caller_sibs):
            a = aC(arg, self)
            a.call()
        else:
            aC(arg)

    def send(self, msg):
        pass

    def add(self, obj):
        # assume contents to be list
        # obj.parent = self  # XXX - ??? consequences?
        # XXX - order may not look "correct", but it is probably right
        #   because of not needing to message the same object twice as
        #   object enters list.
        # FIXME - should NOT do messaging here, use MudAction
        self.msg_children('%s enters.' % obj)
        obj.send('You enter %s' % self)
        self._children.append(obj)

    def remove(self, obj):
        if obj in self._children: 
            self._children.remove(obj)
        # else FIXME put warning
        # FIXME - should NOT do messaging here, use MudAction
        obj.send('You have left %s' % self)
        self.msg_children('%s leaves.' % obj)

    def msg_children(self, msg, omit=[], objs=None):
        if objs:
            O = objs
        else:
            O = self._children
        for o in O:
            if o not in omit:
                o.send(msg)


class MudSprite(MudObject):
    """Anything that is somewhat smart?"""
    def __init__(self, soul=None, *args, **kwargs):
        self.soul = soul
        MudObject.__init__(self, *args, **kwargs)


class MudPlayer(MudSprite):
    def __init__(self, name='Guest', *args, **kwargs):
        MudSprite.__init__(self, *args, **kwargs)
        self._other_souls = []  # XXX - ???
        self.shortdesc = name  # have to be regenerated on title change
        self.name = name
        self.title = ''  # titles are like 'Duke', 'Guildmaster'
        self.cmds = {
            'look': Look,
            'say': Say,
        }  # dictionary of special commands

        # contents...
        # FIXME - uh, better change this to attribute
        self.room = lambda: self._parent
        self.inventory = self._children

    def __str__(self):
        if '%s' in self.title:
            try:
                result = self.title % self.shortdesc
            except:
                # XXX warn?
                result = self.shortdesc
        else:
            result = self.shortdesc
        return result

    def send(self, msg):
        self.soul.send(msg)


class MudRoom(MudObject):
    def __init__(self, shortdesc='Empty Room', *args, **kwargs):
        # generic mudroom
        MudObject.__init__(self, shortdesc=shortdesc, *args, **kwargs)

    def add(self, obj):
        # XXX - fix this and use _parent
        obj.room = self
        return MudObject.add(self, obj)


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

    def do_cmd(self, caller, cmd, arg):
        # XXX - this should be do_cmd
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
            self.soul.send('You logged in as %s/%s' % (self.login, self.password))
            self.soul.send('Logins do not work now, so just exist as a soul without a real body.')
            # XXX - load the body the user originally created.
            body = MudPlayer(name=self.login, soul=self.soul)
            self.soul._parent = body
            # FIXME - this should NOT be here?!
            #self.soul.prompt()
            # FIXME - um, use the queue to move player into room?
            room = self.soul.driver.starting['main']
            room.add(body)
            body._parent = room
            #self.soul.body.room = MudObject()
        return True


class Soul(MudObject):
    """The soul of the connection, takes the request object from a
    connection, which connects to the user.

    This object could inherit from MudRunner and replace what 
    MudThread does.
    """
    # XXX fix this abuse
    def set_body(self, body): self._parent = body
    body = property(
        fget=lambda self: self._parent,
        fset=set_body,
    )

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

        self.cmd_history = []
        self.bad_count = 0
        self.online = None

        self.rawq = []

        # the bodies
        self._parent = SoulGateKeeper(soul=self)
        # no () at the end so not to call it now
        self.cmds = {
            'quit': self.quit,
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
                if line:
                    lines.append(''.join(line))
                    line = []
        if line:
            # append leftovers for next round...
            rawq.append(''.join(line))
        self.rawq = rawq
        LOG.debug('got lines: %s' % str(lines))

        return lines

    def send(self, msg, newline=True):
        try:
            LOG.debug('sending msg: %s' % msg.__repr__())
            # XXX - maybe abstract these telnet codes away, or use the
            # telnet class?
            self.request.send('\xff\xfb\x01%s' % msg)
            if newline:
                # don't send dup newlines
                if msg.__str__()[-2:] != '\r\n':
                    self.request.send('\r\n')
            # reset of some sort for a new line
            self.request.send('\xff\xfc\x01')
        except:
            LOG.warning('cannot send message to %s' % self.__repr__())
            LOG.warning('message was: %s' % msg.__repr__())

    def loop(self):
        if self.online == None:
            self.online = True
            self.send(self.server.greeting_msg, False)

        while self.online:
            try:
                lines = self.recv()
                LOG.debug('%s command count = (%d)' %
                        (str(self.handler.client_address), len(lines)))
                for data in lines:
                    LOG.debug('processing data')
                    # handle command parsing here
                    self.bad_count = 0
                    cmd = data.strip()
                    self.cmd_history.append(cmd)
                    if cmd:
                        LOG.debug('%s cmd: %s' % 
                                (str(self.handler.client_address), 
                                 cmd.__repr__()))
                    # send to queue
                    self.driver.Q(self, cmd)
            except:
                LOG.warning('%s got an exception!' % (self.__repr__()))
                LOG.warning(traceback.format_exc())
                self.send('A serious error has occurred!')
        LOG.debug('%s is offline, terminating connection.' % str(self))

    def handle(self):
        try:
            self.loop()
        except:
            # wow, something messed up bad.
            # currently the login process is _outside_ the exception
            # block, so if login craps out this will definitely be
            # thrown.
            LOG.warning('%s exception has leaked out of loop!' % \
                    (self.__repr__()))
            LOG.warning(traceback.format_exc())
            self.send('A critical error has occured!')
            self.send('You have been disconnected!')

    # support
    def prompt(self):
        self.request.send('\xff\xfd\x01')
        self.request.send(STD_PROMPT)

    def greeting(self):
        LOG.debug('created soul %s' % self)
        self.send('hi %s' % str(self.handler.client_address))

    def quit(self, cmd):
        # XXX - the list cmd sending requires cmd param...
        self.online = False
        self.send('Goodbye %s, see you soon.' % str(self.body.name))
        # FIXME - this need to add the body quit to the queue or body
        # may receive item and item disappears along with deconstruct.


class ChatChannel(MudObject):
    """Chat channel.
    """
    # FIXME - MudObject
    def __init__(self, *args, **kwargs):
        # change children to set()?
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

