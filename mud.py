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

# list of souls (or connections)
souls = []


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


class Soul():
    """The soul of the connection, takes the request object from a
    connection, which connects to the user.
    """
    def __init__(self, handler):
        self.handler = handler
        self.request = handler.request

        self.cmd_history = []
        self.bad_count = 0
        self.parse = True
        # StringIO will be better choice for buffer.
        self.buffer = ''

    # communcation
    def recv(self):
        data = self.request.recv(MAX_CMD_LEN)
        return data

    def send(self, msg):
        try:
            self.request.send(msg)
        except:
            logging.warning('cannot send message to %s' % self)
            logging.warning('message was\n%s' % msg)

    def loop(self):
        while True:
            try:
                data = self.recv()
                if not data:
                    return
                logging.debug('%s data: (%d)' %
                        (str(self.handler.client_address), len(data)))
                # handle command parsing here
                # parse(data)
                if self.parse:
                    self.bad_count = 0
                    cmd = data.strip()
                    self.cmd_history.append(cmd)
                    if cmd:
                        logging.debug('%s cmd: %s' % 
                                (str(self.handler.client_address), cmd))
                    # TODO - command lookup table here
                    if cmd == 'view':
                        msg = 'souls = %s\n' % str(self)
                        self.send(msg)
                    if cmd == 'history':
                        msg = 'history = %d\n' % len(self.cmd_history)
                        self.send(msg)
                    elif cmd == 'except':
                        raise
                    elif cmd == 'bye':
                        return True
                    else:
                        self.send('You sent: %s' % data)
                else:
                    logging.debug('Last chunk too long, scanning for next newline')
                    self.bad_count += 1

                if self.bad_count > MAX_BAD:
                    logging.debug('bad_count maxxed out, dropping connection')
                    return

                # if data did end with newline, parse
                self.parse = (data[-1] == '\n')
                print self.parse
            except:
                logging.warning('%s got an exception!' % str(self))
                logging.warning(traceback.format_exc())
                self.send('A serious error has occured!\n')

    def handle(self):
        try:
            self.loop()
        except:
            # wow, something messed up bad.
            logging.warning('%s exception has leaked out of loop!' % str(self))
            logging.warning(traceback.format_exc())
            self.send('A critical error has occured!\nYou have been disconnected!\n')

    # support
    def greeting(self):
        logging.debug('created soul %s' % self)
        self.send('hi %s\n' % str(self.handler.client_address))

    def quit(self):
        self.send('bye %s\n' % str(self.handler.client_address))

def start():
    server = None
    try:
        print "Starting server...",
        server = ThreadingMudServer((HOST, PORT), MudRequestHandler)
        print "done."
    except socket.error:
        print "fail!"
        raise

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
                    soul.send('Server shutting down.\n')
            finally:
                server.server_close()
        else:
            raise
        sys.exit()

if __name__ == '__main__':
    start()
