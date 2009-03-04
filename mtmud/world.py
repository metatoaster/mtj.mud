from MudObjects import MudArea, MudRoom, MudRoomLink

# These classes could be quite temporary.
class Foundation(MudArea):
    """Base area"""
    def __init__(self, *args, **kwargs):
        MudArea.__init__(self, *args, **kwargs)
        startroom = StartRoom()
        flossroom = FlossRoom()
        greenroom = GreenRoom()

        MudRoomLink(link=((startroom, 'down'), (flossroom, 'up')))
        MudRoomLink(link=((flossroom, 'east'), (greenroom, 'west')))

        self.add(startroom)
        self.add(flossroom)
        self.add(greenroom)


_StartRoom = """\
  A sense of tranquility falls upon you as you enter into this expanse.
Thin, wispy tendrils of white vapor enshrouds everything; they rise and 
fall as if orchestrating a dance.  As you bring your gaze further away,
you find the mist obscuring the source of the white glow, rendering its
glow to be soothing on your eyes rather than blinding.  Since the light
casts from every direction, shadows cannot hold their presences here.
""".replace('\n', '\r\n')

class StartRoom(MudRoom):
    def __init__(self, *args, **kwargs):
        MudRoom.__init__(self, *args, **kwargs)
        self.shortdesc = 'White Expanse'
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
