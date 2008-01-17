# mtmud.mud - A Basic Mud library in Python
# Copyright (c) 2007 Tommy Yu
# This software is released under the GPLv3

import logging
from config import *
from mtmud.server import *
from mtmud.runner import *

# XXX - perhaps move this to a local logging class
logging.basicConfig(level=logging.WARNING)
logging.addLevelName(9, 'DEBUG-1')
logging.addLevelName(8, 'DEBUG-2')
logging.addLevelName(1, 'DEBUG-9')

def setLogLevel(level):
    logging.root.setLevel(level)
