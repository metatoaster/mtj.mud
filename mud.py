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
from config import *

logging.basicConfig(level=logging.DEBUG)


#class MudEvent(MudObject):
#    """\
#    Anything an event happens, this gets created.
#    """
#    def __init__(self, source=None, target=None, *args, **kwargs):
#        self._parent = source
#        self.target = target
