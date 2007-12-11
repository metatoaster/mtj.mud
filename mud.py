import sys
import socket
import SocketServer

HOST = ''
PORT = 50000
MAX_CMD_LEN = 1024
MAX_BAD = 10

# list of souls (or connections)
souls = []


class ThreadingMUDServer(SocketServer.ThreadingTCPServer):
    allow_reuse_address = True
    pass


class MudRequestHandler(SocketServer.BaseRequestHandler):
    def setup(self):
        print self.client_address, 'connected.'
        soul = Soul(self.request)
        soul.send('hi ' + str(self.client_address) + '\n')
        souls.append(soul)
        self.soul = soul
        self.cmd_history = []
        self.bad_count = 0
        self.parse = True
        # StringIO will be better choice for buffer.
        self.buffer = ''

    def handle(self):
        soul = self.soul
        try:
            while 1:
                # data larger than this is broken into separate part
                data = self.request.recv(MAX_CMD_LEN)
                if not data:
                    return
                print '%s data: (%d)' % (self.client_address, len(data))
                # handle command parsing here
                # parse(data)
                if self.parse:
                    self.bad_count = 0
                    cmd = data.strip()
                    self.cmd_history.append(cmd)
                    if cmd:
                        print '%s cmd: %s' % (self.client_address, cmd)
                    # TODO - command lookup table here
                    if cmd == 'view':
                        msg = 'souls = %s\n' % str(souls)
                        soul.send(msg)
                    if cmd == 'history':
                        msg = 'history = %d\n' % len(self.cmd_history)
                        soul.send(msg)
                    elif cmd == 'except':
                        raise
                    elif cmd == 'bye':
                        return
                    else:
                        soul.send(data)
                else:
                    print 'Last chunk too long, scanning for next newline'
                    self.bad_count += 1
                # if data did end with newline, parse
                if self.bad_count > MAX_BAD:
                    print 'bad_count maxxed out, dropping connection'
                    return
                self.parse = (data[-1] == '\n')

        except:
            print self.client_address, 'got an exception!'
            return

    def finish(self):
        print self.client_address, 'disconnected.'
        try:
            soul = self.soul
            souls.remove(soul)
            soul.send('bye ' + str(self.client_address) + '\n')
        except:
            print 'error sending goodbye'


class Soul():
    def __init__(self, request):
        self.request = request
        print "creating soul %s" % self

    def recv(self):
        pass

    def send(self, msg):
        self.request.send(msg)

def start():
    server = None
    try:
        print "Starting server...",
        server = ThreadingMUDServer((HOST, PORT), MudRequestHandler)
        print "done."
        while 1:
            server.handle_request()
    except KeyboardInterrupt:
        print "Got Keyboard Interrupt."
    except socket.error:
        print "fail!"
        raise
    finally:
        if server:
            try:
                print "Server shutting down."
                for v in souls:
                    v.send('Server shutting down.\n')
            finally:
                server.server_close()
        else:
            raise
        sys.exit()

if __name__ == '__main__':
    start()
