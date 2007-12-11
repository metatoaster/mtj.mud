# mtmud.mud - A Basic Mud library in Python
# Copyright (c) 2007 Tommy Yu
# This software is released under the GPLv3

import sys
import socket
import SocketServer
import logging
import traceback

logging.basicConfig(level=logging.DEBUG)

HOST = ''
PORT = 50000
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
valid_cmd = ['say', 'yell',]


class MudThread:
    """Mix-in class to handle each request in a new thread."""

    # Decides how threads will act upon termination of the
    # main process
    daemon_threads = False

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
        import threading
        t = threading.Thread(target = self.process_request_thread,
                             args = (request, client_address))
        if self.daemon_threads:
            t.setDaemon (1)
        t.start()


class ThreadingMudServer(MudThread, SocketServer.TCPServer):
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
        try:
            soul.quit()
        except:
            logging.warning('error sending goodbye to %s' % 
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
            self.soul.send('Logins do not work now, so just exist as a soul without a body.')
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

    # communication
    def recv(self):
        # TODO - this can be made more efficient
        validChar = lambda x: 32 <= ord(x) <= 126
        data = ''
        rawq = self.rawq
        while self.online:
            data = self.request.recv(32)
            logging.log(0, 'received data (%02d|%s)' % 
                    (len(data), data.__repr__()))
            if not data:
                self.online = False
            if data: # and validChar(data):
                rawq.append(data)
            if CHAR_TERM in data:
                # XXX I am tired
                break

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
            logging.warning('%s exception has leaked out of loop!' % str(self))
            logging.warning(traceback.format_exc())
            self.send('A critical error has occured!')
            self.send('You have been disconnected!')

    # commands
    def processCmd(self, cmd, trail=''):
        if cmd in valid_cmd:
            self.send('Valid command was sent')
            self.send(STD_PROMPT, False)
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
        self.send('bye %s' % str(self.handler.client_address))



def start():
    server = None
    try:
        print "Starting server...",
        server = ThreadingMudServer((HOST, PORT), MudRequestHandler)
        print "done."
    except socket.error:
        print "fail!"
        raise

    # XXX - split this part off?
    try:
        while 1:
            server.handle_request()
    except KeyboardInterrupt:
        print "Got Keyboard Interrupt."
    finally:
        if server:
            try:
                print "Server shutting down."
                for soul in souls:
                    soul.send('Server shutting down.')
            finally:
                server.server_close()
        else:
            raise
        sys.exit()

if __name__ == '__main__':
    start()
