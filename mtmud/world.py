from MudObjects import MudArea, MudRoom  #, MudExit

# These classes could be quite temporary.
class Foundation(MudArea):
    """Base area"""
    def __init__(self, *args, **kwargs):
        MudArea.__init__(self, *args, **kwargs)
        self.add(StartRoom())
        self.add(FlossRoom())
        self.add(GreenRoom())


_StartRoom = """\
    Upon entering this room, you feel a sense of tranquility fall upon
you.  Thin, wispy tendrils of white vapor enshrouds everything; they
rise and fall as if orchestrating a dance.  Further away, the vapor
becomes thicker, yet not thick enough to prevent the soothing white
light beyond from filtering through.  The white light is bright, yet
soothing on your eyes, casts its rays on from all angles on everything
in this room, easily dispelling most, if not all, shadows away.
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


_GreenRoom = """\
    You are in a room with walls covered in lime green wallpaper.  Upon
closer inspection of the wallpaper you notice it's made of very fine
strands of delicious candy floss aligned vertically.
""".replace('\n', '\r\n')

class GreenRoom(MudRoom):
    def __init__(self, *args, **kwargs):
        MudRoom.__init__(self, *args, **kwargs)
        self.shortdesc = 'Green Room'
        self.longdesc = _GreenRoom
