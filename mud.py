# mtmud.mud - A Basic Mud library in Python
# Copyright (c) 2007 Tommy Yu
# This software is released under the GPLv3

import sys
import socket
import SocketServer
import logging
import traceback
import threading

# workaround for locked sockets
socket.setdefaulttimeout(0.5)

logging.basicConfig(level=logging.DEBUG)

HOST = ''
PORT = 50000
MAX_DATA_LEN = 512
MAX_CMD_LEN = 1024
MAX_BAD = 10
CMD_TERM = ['\r', '\n']
CHAR_TERM = '\r'

LOGIN_PROMPT = '\xff\xfc\x01Login: '
PASSWORD_PROMPT = '\xff\xfb\x01Password: '
STD_PROMPT = '> '

# list of souls (or connections)
souls = []

# list of valid commands need to be placed somewhere else better
valid_cmd = {
    'say': lambda: False,
    'yell': lambda: False,
}


class MudDriver:
    """The mud driver.
    
    This is where main events should execute in.
    """


class MudConnThread:
    """Mix-in class to handle each request in a new thread."""

    # Decides how threads will act upon termination of the
    # main process
    daemon_threads = True

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
        if self.daemon_threads:
            t.setDaemon (1)
        t.start()


class ThreadingMudServer(MudConnThread, SocketServer.TCPServer):
    """Standard ThreadingTCPServer, extended to allow customization.
    """
    allow_reuse_address = True
    pass


class MudRequestHandler(SocketServer.BaseRequestHandler):
    """Mud request handler

    Basically sets up a soul object and pass the request controls to
    it.  This may be redesigned in the future.
    """
    def setup(self):
        logging.debug('%s connected' % str(self.client_address))
        soul = Soul(self)
        self.soul = soul
        souls.append(soul)

    def handle(self):
        self.soul.handle()

    def finish(self):
        soul = self.soul
        if soul in souls:
            # bye
            souls.remove(soul)
        logging.debug('%s disconnecting' % 
                str(self.client_address))


class MudObject(object):
    # FIXME - use kwargs, etc. for constructor
    def __init__(self, description=''):
        self.description = description


class MudRoom(MudObject):
    def __init__(self, description=''):
        # generic mudroom
        MudObject.__init__(self, description)
        self.cmds = {'look': self.look}  # dictionary of special commands

    # XXX - need better name for generic activate room method
    def enter(self):
        # show description
        return self.description

    def look(self):
        return self.description

    def processCmd(self, cmd):
        # special commands
        return self.cmds[cmd]()

    def valid_cmds(self, cmd):
        return cmd in self.cmds


class LoginRoom(MudRoom):  # should also inherit from special subclass

    def __init__(self, soul):
        MudObject.__init__(self, 'Welcome to the MUD.\r\n')
        self.soul = soul
        self.login = None
        self.password = None
        self.valid_cmds = lambda x:True

    def enter(self, soul):
        # XXX - why do we want a soul here?
        result = ''.join([self.description, LOGIN_PROMPT])
        return result

    def processCmd(self, cmd):
        # these sends directly to souls here are probably bad practice
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
            self.soul.body = self.login
            self.soul.send(STD_PROMPT, False)
            # manual move...
            self.soul.room = Rooms['main']
        return True


# this basically creates an instance?
SpecialObject = {
    'Login': LoginRoom,
}

Rooms = {
    'main': MudRoom('An empty room.'),
}

class Soul():
    """The soul of the connection, takes the request object from a
    connection, which connects to the user.
    """
    def __init__(self, handler):
        self.handler = handler
        self.request = handler.request

        self.cmd_history = []
        self.bad_count = 0
        self.online = None

        self.rawq = []

        # the bodies
        self.body = None
        self.room = SpecialObject['Login'](self)
        # no () at the end so not to call it now
        self.valid_cmd = {
            'quit': self.quit,
        }

    # communication
    def recv(self):
        # TODO - this can be made more efficient
        validChar = lambda x: 32 <= ord(x) <= 126
        data = ''
        rawq = self.rawq
        while self.online and CHAR_TERM not in data:
            data = self.request.recv(MAX_DATA_LEN)
            logging.log(0, 'received data (%02d|%s)' % 
                    (len(data), data.__repr__()))
            if not data:
                self.online = False
            if data: # and validChar(data):
                rawq.append(data)

        # do error validation here.
        # else:
        #     logging.debug('Last chunk too long, scanning for next newline')
        #     self.bad_count += 1
        # if self.bad_count > MAX_BAD:
        #     logging.debug('bad_count maxxed out, dropping connection')
        #     return

        # fresh queue after we grabbed output
        raw = ''.join(rawq)
        rawq = []

        lines = []  # all the good lines
        line = []   # current line (chars)
        for c in raw:
            if validChar(c):
                line.append(c)
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
                self.request.send('\r\n')
            # reset of some sort for a new line
            self.request.send('\xff\xfc\x01')
        except:
            logging.warning('cannot send message to %s' % self)
            logging.warning('message was: %s' % msg.__repr__())

    def loop(self):
        if self.online == None:
            self.online = True
            self.send(self.room.enter(self), False)

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
                                (str(self.handler.client_address), cmd))
                    # TODO - command lookup table here
                    self.processCmd(cmd)
                    #if cmd == 'view':
                    #    msg = 'souls = %s' % str(self)
                    #    self.send(msg)
                    #if cmd == 'history':
                    #    msg = 'history = %d' % len(self.cmd_history)
                    #    self.send(msg)
                    #elif cmd == 'except':
                    #    raise Exception('user triggered exception')
                    #elif cmd == 'bye':
                    #    return True
                    #else:
                    #    self.send('You sent: %s' % data)
            except:
                logging.warning('%s got an exception!' % str(self))
                logging.warning(traceback.format_exc())
                self.send('A serious error has occured!')
        logging.debug('%s is offline, terminating connection.' % str(self))

    def handle(self):
        try:
            self.loop()
        except:
            # wow, something messed up bad.
            # currently the login process is _outside_ the exception
            # block, so if login craps out this will definitely be
            # thrown.
            logging.warning('%s exception has leaked out of loop!' % str(self))
            logging.warning(traceback.format_exc())
            self.send('A critical error has occured!')
            self.send('You have been disconnected!')

    # commands
    def processCmd(self, cmd, trail=''):
        if cmd in valid_cmd:
            self.send('Valid global command was sent')
            valid_cmd[cmd]()
            self.send(STD_PROMPT, False)
        elif cmd in self.valid_cmd:
            self.send('Valid soul command was sent')
            self.valid_cmd[cmd]()
            # Prompt handling *will* need fixing
            #self.send(STD_PROMPT, False)
        #elif cmd in self.room.cmds:
        elif self.room.valid_cmds(cmd):
            # bad code is bad
            s = self.room.processCmd(cmd)
            logging.debug('room cmd: %s' % cmd)
            logging.debug('room result: %s' % s)
            if type(s) is str:
                self.send(s)
                self.send(STD_PROMPT, False)
        else:
            #self.send('You sent: %s' % data)
            self.send('"%s" is not valid command' % cmd)
            self.send(STD_PROMPT, False)

    # support
    def greeting(self):
        logging.debug('created soul %s' % self)
        self.send('hi %s' % str(self.handler.client_address))

    def quit(self):
        self.online = False
        self.send('Goodbye %s, see you soon.' % str(self.body))


class MudServer():

    def __init__(self):
        """Initalizes the server, set constants from config file, etc.
        
        Does nothing for now.
        """
        self.running = None
        self.server = None
        self.souls = []
        self.t = None

    def _begin(self):
        try:
            logging.info('Starting server...')
            self.server = ThreadingMudServer((HOST, PORT), MudRequestHandler)
            self.running = True
            logging.info('Started server %s', self)
        except socket.error:
            logging.warn('Failed to start server %s', self)
            raise

    def _run(self):
        while self.running:
            self.server.handle_request()

    def _end(self):
        if self.server and self.running:
            try:
                logging.info('Shutting down server %s.', self)
                # FIXME - deal with threads?!
                for soul in self.souls:
                    soul.send('Server shutting down.')
            finally:
                self.server.server_close()
                self.running = False
        else:
            raise
        #sys.exit()

    def _start(self):
        # XXX - this is not a real start function, stuck in loop is
        # still very stuck in loop.
        self._begin()
        try:
            self._run()
        finally:
            self._end()

    def start(self):
        """Start a new thread to process the request."""
        self.t = threading.Thread(target = self._start)
        self.t.start()

    def stop(self):
        """Terminates server."""
        # need to join self.t?
        self._end()
        self.t.join(5)
        self.t.isAlive()


if __name__ == '__main__':
    def start():
        if not mudserv.running:
            print 'Starting mudserv... ',
            mudserv.start()
            print 'done.'
        else:
            print 'mudserv already started.'

    def stop():
        if mudserv.running:
            print 'Stopping mudserv... ',
            mudserv.stop()
            print 'done.'
        else:
            print 'mudserv not started.'

    def quit():
        # lolhack
        raise EOFError

    mudserv = MudServer()
    active = True
    server_cmd = {
         'start': start,
         'stop': stop,
         'quit': quit,
    }

    print 'Starting mtmud interactive shell.'
    while active:
        try:
            print('mudctrl>'),
            s = raw_input()
            if s in server_cmd:
                server_cmd[s]()
            else:
                print 'Invalid Command.'
        except EOFError:
            active = False
            print ''
        except KeyboardInterrupt:
            print('\nGot keyboard interrupt, terminating.')
            active = False
        except:
            print traceback.format_exc()
    # stop server if running
    if mudserv.running:
        mudserv.stop()

