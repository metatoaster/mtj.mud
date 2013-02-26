import socket
from SocketServer import TCPServer, BaseRequestHandler
import logging
import threading

from config import *
from objects import *

LOG = logging.getLogger('mtj.mud.server')

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
            soul.quit()


class MudRequestHandler(BaseRequestHandler):
    """Mud request handler

    Basically sets up a soul object and pass the request controls to
    it.  This may be redesigned in the future.
    """
    def setup(self):
        LOG.debug('%s connected', str(self.client_address))
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
        LOG.debug('%s disconnecting', str(self.client_address))

