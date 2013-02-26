#!/bin/env python2.5
# Copyright (c) 2007 Tommy Yu
# This software is released under the GPLv3

# Interactive controller for mtj.mud

from sys import stdout
import mtj.mud
from mtj.mud import *
try:
    import readline
except:
    pass

class mudctrl:

    def __init__(self):
        # XXX - objects by these 3 lines could be constructed as one in a 
        # startup class.
        self.driver = mtj.mud.MudDriver()
        self.mudserv = mtj.mud.MudServerController(host=HOST, port=PORT)
        self.driver.add(self.mudserv)
        self.active = True
        self.eval_mode = False

        self.prompts = {
            True: '>>> ',
            False: 'mudctrl> ',
        }
        self.root_server_cmd = {
             'start': self.start,
             'stop': self.stop,
             'quit': self.quit,
             'drive': self.drive,
             'brake': self.brake,
             'level': self.level,
             'port': self.port,
             'debug()': self.debug,
             '': str,  # lolhack
        }

    def _parse_cmd(self, arg):
        x = arg.split(' ', 1)
        if len(x) > 1:
            return x
        else:
            return (arg, None)

    def start(self, arg=None):
        if not self.mudserv.isRunning():
            print 'Starting mudserv thread.'
            self.mudserv.start()
        else:
            print 'mudserv already started.'

    def stop(self, arg=None):
        if self.mudserv.isRunning():
            print 'Stopping mudserv...',
            stdout.flush()
            self.mudserv.stop()
            print 'done.'
        else:
            print 'mudserv not started.'

    def drive(self, arg=None):
        if not self.driver.isRunning():
            print 'Starting driver thread.'
            self.driver.start()
        else:
            print 'driver already driving.'

    def brake(self, arg=None):
        if self.driver.isRunning():
            print 'Stopping driver...',
            stdout.flush()
            self.driver.stop()
            print 'done.'
        else:
            print 'driver not driving.'

    def port(self, arg=None):
        # XXX - range checking
        if arg and arg.isdigit():
            port = int(arg)
            self.mudserv.port = port
            print 'mudserv.port = %d' % port
        else:
            print 'Usage: port <num>'

    def level(self, arg=None):
        if arg and arg.isdigit():
            level = int(arg)
            mtj.mud.setLogLevel(level)
            print 'Log level set to %s' % logging.getLevelName(level)
        else:
            # XXX perhaps use the string identifiers for level id also
            print 'Usage: level <num>'

    def debug(self, arg=None):
        # lolhack
        if not self.eval_mode:
            print('Debug mode on.  Basic raw Python commands are now accepted.')
            print('To return to standard mudctrl mode, type "mud.debug()" or send EOF.')
        self.eval_mode = not self.eval_mode
        if not self.eval_mode:
            return 'Debug mode off.'

    def quit(self, arg):
        # lolhack
        raise EOFError

    def run(mud):
        # XXX cheese
        import __builtin__ as __builtins__

        print 'Starting mtj.mud interactive shell.'
        while mud.active:
            try:
                # XXX might want to use code.InteractiveConsole
                mud._s = raw_input(mud.prompts[mud.eval_mode])
                if mud.eval_mode:
                    try:
                        print eval(mud._s)
                    except:
                        exec mud._s
                else:
                    mud.args = mud._parse_cmd(mud._s)
                    if mud.args[0] in mud.root_server_cmd:
                        mud.root_server_cmd[mud.args[0]](mud.args[1])
                    else:
                        print 'Invalid Command.'
            except EOFError:
                if mud.eval_mode:
                    mud.eval_mode = False
                else:
                    mud.active = False
                print ''
            except KeyboardInterrupt:
                print('\nGot keyboard interrupt.'),
                if mud.mudserv.isRunning():
                    print('mudserv running, stopping...'),
                    mud.mudserv.stop()
                    print 'done.'
                else:
                    print('mudserv not running, terminating.')
                    mud.active = False
            except:
                print traceback.format_exc()
        # stop server if running
        mud.stop()
        mud.brake()

