from MudObjects import MudArea, MudRoom, MudExit

# These classes could be quite temporary.
class Foundation(MudArea):
    """Base area"""
    def __init__(self, *args, **kwargs):
        MudArea.__init__(self, *args, **kwargs)
        s = StartRoom()
        self.add(s)
        self.add(FlossRoom())


_StartRoom = """\
    Upon entering this room, you feel a sense of tranquility fall upon
you.  All around you, wispy tendrils of white vapour rise and fall, as
if they were trying to orchestrate a dance.  Gazing beyond the vapors,
soothing white light filters through the clouds all around you, calmly
basking everything in this room in its white, shadow-less glow.
""".replace('\n', '\r\n')

class StartRoom(MudRoom):
    def __init__(self, *args, **kwargs):
        MudRoom.__init__(self, *args, **kwargs)
        self.shortdesc = 'Entry Room'
        self.longdesc = _StartRoom


_FlossRoom = """\
You are in a green delicious room.  The wallpaper looks like it might be
made of candy floss.
""".replace('\n', '\r\n')

class FlossRoom(MudRoom):
    def __init__(self, *args, **kwargs):
        MudRoom.__init__(self, *args, **kwargs)
        self.shortdesc = 'Floss Room'
        self.longdesc = _FlossRoom

