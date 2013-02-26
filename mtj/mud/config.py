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

