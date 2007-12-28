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

logging.basicConfig(level=logging.DEBUG)

HOST = '0.0.0.0'
PORT = 50000
LISTEN_TIMEOUT = 1  # seconds
MAX_DATA_LEN = 512
MAX_CMD_LEN = 1024
MAX_BAD = 10
CMD_TERM = ['\r', '\n']
CHAR_TERM = '\r'

LOGIN_PROMPT = '\xff\xfc\x01Login: '
PASSWORD_PROMPT = '\xff\xfb\x01Password: '
STD_PROMPT = '> '

GREETING = """\
Welcome to the MUD!

This playground is written in Python.  Everything is still very basic,
if it even works at all.  No player profiles yet, but let's pretend
they work for now.  Just type in anything for login (which will be your
name) and password.

Login: """.replace('\n', '\r\n')  # lol?

DEFAULT_ROOM_DESC = """\
This is the default room description for a newly created room if no
description is passed in the construction parameter.  Although this is 
a very bland and featureless room, all the functions found in normal
rooms can be utilized, so feel free to look around, even though you may
find nothing of importance aside from other objects that may be sitting
around in this room.
""".replace('\n', '\r\n')  # lol?


class MudConnThread:
    """Based on ThreadingMixIn of the SocketServer module.
    """

    # XXX - is joining the threads on shutdown required?

    def process_request_thread(self, request, client_address):
        """Same as in BaseServer but as a thread.

        In addition, exception handling is done here.

        """
        try:
            self.finish_request(request, client_address)
            self.close_request(request)
        except:
            self.handle_error(request, client_address)
            self.close_request(request)

    def process_request(self, request, client_address):
        """Start a new thread to process the request."""
        t = threading.Thread(target = self.process_request_thread,
                             args = (request, client_address))
        t.setDaemon(1)
        t.start()


class ThreadingMudServer(MudConnThread, TCPServer):
    """Standard ThreadingTCPServer, extended to allow customization.
    """
    allow_reuse_address = True

    def __init__(self, server_address, RequestHandlerClass, controller):
        """Constructor.  May be extended, do not override."""
        TCPServer.__init__(self, server_address, RequestHandlerClass)
        # XXX - controller = MudMaster?
        self.controller = controller
        self.active = True
        self.souls = []
        self.greeting_msg = GREETING

    def get_request(self):
        """Get the request and client address from the socket.

        Don't want to be stuck listening forever.

        """

        self.socket.settimeout(LISTEN_TIMEOUT)
        return self.socket.accept()

    def server_close(self):
        TCPServer.server_close(self)
        self.active = False
        for soul in self.souls:
            soul.send('Server shutting down.')
            soul.quit('')


class MudRequestHandler(BaseRequestHandler):
    """Mud request handler

    Basically sets up a soul object and pass the request controls to
    it.  This may be redesigned in the future.
    """
    def setup(self):
        logging.debug('%s connected' % str(self.client_address))
        soul = Soul(self)
        self.soul = soul
        self.server.souls.append(soul)

    def handle(self):
        if self.server.active:
            self.soul.handle()

    def finish(self):
        soul = self.soul
        if soul in self.server.souls:
            # bye
            self.server.souls.remove(soul)
        logging.debug('%s disconnecting' % str(self.client_address))


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
        logging.debug('%s.process_cmd [%s, %s]' % \
                (self.__repr__(), cmd.__repr__(), arg.__repr__()))
        if self.valid_cmd(cmd):
            logging.debug('%s.process_cmd, cmd in self' % (self.__repr__()))
            result = self.do_cmd(self, cmd, arg)
            #selfMsg, targetMsg, othersMsg = self.cmds[cmd](msg)
        elif self._parent and self._parent.valid_cmd(cmd):
            logging.debug('%s.process_cmd, cmd in parent %s' % 
                    (self.__repr__(), self._parent.__repr__()))
            result = self._parent.do_cmd(self, cmd, arg)
            #selfMsg, targetMsg, othersMsg = self._parent.cmds[cmd](msg)
        else:
            # search children
            for child in self._children: 
                if child.valid_cmd(cmd):
                    logging.debug('%s.process_cmd, cmd in children %s' %
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
                    logging.debug('%s.process_cmd, cmd in sibling %s' %
                            (self.__repr__(), child.__repr__()))
                    result = child.do_cmd(self, cmd, arg)
                    #selfMsg, targetMsg, othersMsg = child.cmds[cmd](msg)
                    break

    def valid_cmd(self, cmd):
        return cmd in self.cmds

    def do_cmd(self, caller, cmd, arg):
        # FIXME - this is NOT what I designed.
        logging.debug('%s.do_cmd(%s, %s, %s)' % \
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


class MudEvent(MudObject):
    """\
    Anything an event happens, this gets created.
    """
    def __init__(self, source=None, target=None, *args, **kwargs):
        self._parent = source
        self.target = target


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
            'look': self.look,
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

    def look(self, cmd):
        if self.room:
            if hasattr(self.room, 'look'):
                return self.room.look(cmd)
            else:
                logging.warning('%s in %s has no look()' % (self.__repr__(), self._parent.__repr__()))
                return "You are somewhere but for some reason you can't look!"
        else:
            return "You are not in a room!"

    def say(self, cmd):
        # XXX - should probably use a proper command type
        if len(cmd) <= 1:
            return "Talking to yourself is a sign of impending mental collapse."
        msg = cmd[1]
        if self.room:
            self.send('You say, "%s"' % msg)
            self.room.msg_children('%s says, "%s"' % (self.name, msg),
                    omit=[self])
            return True
        else:
            return "You are not in a room!"

    def send(self, msg):
        self.soul.send(msg)


class MudRoom(MudObject):
    def __init__(self, shortdesc='Empty Room', *args, **kwargs):
        # generic mudroom
        MudObject.__init__(self, shortdesc=shortdesc, *args, **kwargs)
        self.cmds = {'look': self.look}  # dictionary of special commands

    def look(self, cmd):
        """Look command.  Example output might be something like:

        Empty Room

        This is a very empty room.
                There are no obvious exits.

         Player
         Guest
         Somebody

        """
        template = '%s\r\n\r\n%s\r\n' % (self.shortdesc, self.longdesc)
        template += '        There are no obvious exits.\r\n'
        # lolhax
        if self._children:
            template += '\r\n'
        # XXX - one can see oneself in the room
        for o in self._children:
            template += ' %s\r\n' % o.shortdesc
        return template

    def add(self, obj):
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
            room = Rooms['main']
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
                logging.log(0, 'received data (%02d|%s)' % 
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
        #     logging.debug('Last chunk too long, scanning for next newline')
        #     self.bad_count += 1
        # if self.bad_count > MAX_BAD:
        #     logging.debug('bad_count maxxed out, dropping connection')
        #     return

        # fresh queue after we grabbed output
        raw = ''.join(rawq)
        logging.debug('Received raw data: %s', raw.__repr__())
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
                    logging.debug('acting on iac')
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
        logging.debug('got lines: %s' % str(lines))

        return lines

    def send(self, msg, newline=True):
        try:
            logging.debug('sending msg: %s' % msg.__repr__())
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
            logging.warning('cannot send message to %s' % self.__repr__())
            logging.warning('message was: %s' % msg.__repr__())

    def loop(self):
        if self.online == None:
            self.online = True
            self.send(self.server.greeting_msg, False)

        while self.online:
            try:
                lines = self.recv()
                logging.debug('%s command count = (%d)' %
                        (str(self.handler.client_address), len(lines)))
                for data in lines:
                    logging.debug('processing data')
                    # handle command parsing here
                    self.bad_count = 0
                    cmd = data.strip()
                    self.cmd_history.append(cmd)
                    if cmd:
                        logging.debug('%s cmd: %s' % 
                                (str(self.handler.client_address), 
                                 cmd.__repr__()))
                    # send to queue
                    self.driver.Q(self, cmd)
            except:
                logging.warning('%s got an exception!' % (self.__repr__()))
                logging.warning(traceback.format_exc())
                self.send('A serious error has occurred!')
        logging.debug('%s is offline, terminating connection.' % str(self))

    def handle(self):
        try:
            self.loop()
        except:
            # wow, something messed up bad.
            # currently the login process is _outside_ the exception
            # block, so if login craps out this will definitely be
            # thrown.
            logging.warning('%s exception has leaked out of loop!' % \
                    (self.__repr__()))
            logging.warning(traceback.format_exc())
            self.send('A critical error has occured!')
            self.send('You have been disconnected!')

    # support
    def prompt(self):
        self.request.send('\xff\xfd\x01')
        self.request.send(STD_PROMPT)

    def greeting(self):
        logging.debug('created soul %s' % self)
        self.send('hi %s' % str(self.handler.client_address))

    def quit(self, cmd):
        # XXX - the list cmd sending requires cmd param...
        self.online = False
        self.send('Goodbye %s, see you soon.' % str(self.body.name))
        # FIXME - this need to add the body quit to the queue or body
        # may receive item and item disappears along with deconstruct.


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

    def __init__(self, *args, **kwargs):
        """\
        Initializes the controller, set constants from config file, etc.
        
        Currently does nothing too important for now.
        """
        MudRunner.__init__(self, *args, **kwargs)
        self.server = None
        self.driver = None
        self.chats = {}
        self.chats['global'] = ChatChannel()
        self.listenAddr = (HOST, PORT)  # redefine from somewhere?

    def _begin(self):
        if self._running:
            logging.warn('Server %s already started.' % self.server)
            return
        try:
            logging.info('Starting server...')
            self.server = ThreadingMudServer(
                    self.listenAddr, MudRequestHandler, self)
            logging.info('Started server %s', self.server)
        except socket.error:
            logging.warn('Failed to start server %s', self.server)
            raise

    def _action(self):
        self.server.handle_request()

    def _end(self):
        if self.server and self._running:
            # XXX - needed here, server_close could toss exception
            logging.info('Shutting down server %s.', self.server)
            self.server.server_close()
        else:
            logging.debug('No running server to stop.')


class MudDriver(MudRunner):
    """\
    The mud driver.
    
    This is what drives all actions in the mud, or where main events
    spawned by objects of the world should execute in.
    """
    def __init__(self, *args, **kwargs):
        MudRunner.__init__(self, *args, **kwargs)
        self.world = []
        self.cmdQ = deque()
        self.timeout = 1 / 1000.
        self._build_world()

    def _begin(self):
        pass

    def _action(self):
        while self.cmdQ:
            # nobody else is popping this list, so when this is true
            # there must be an item to pop.  No false positives either
            # as append is atomic.
            caller, cmd = self.cmdQ.popleft()
            # FIXME
            logging.debug('cmdQ -> %s: %s' % (caller.__repr__(), cmd))
            try:
                caller.process_cmd(cmd)
            except:
                logging.warning(
                    "%s got an exception: command '%s' from %s" %\
                    (self.__repr__(), cmd.__repr__(), caller.__repr__()))
                logging.warning(traceback.format_exc())
                caller.send('A serious error has occurred!')
            # parse cmd
        # all done, go sleep for a bit.
        time.sleep(self.timeout)

    def _end(self):
        # save the world!
        pass

    def _build_world(self):
        # builds the world
        pass

    def Q(self, caller, cmd):
        """\
        Queue a command.  Commands are just strings.
        """
        logging.debug('cmdQ <- %s: %s' % (caller.__repr__(), cmd))
        self.cmdQ.append((caller, cmd,))
        # this is an atomic operation.


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


Rooms = {
    'main': MudRoom(shortdesc='Empty Room', longdesc=DEFAULT_ROOM_DESC),
}
