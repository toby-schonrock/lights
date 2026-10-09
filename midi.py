import mido

from examples import DimmerOverlay, RainbowsPanel
from lib.artnetcontroller import ArtNetController
from lib.scenes import Scene

controller = ArtNetController("192.168.1.169")

dimmer = DimmerOverlay()
scene = Scene(RainbowsPanel(), [dimmer], lambda lights: controller.send_packet(lights.get_channel_values()))
scene.start()
# scene = Scene(RainbowsPanel(), [dimmer], lambda lights: None)

devname = "Akai LPD8 Wireless:Akai LPD8 Wireless MIDI 1 20:0"

lastvalue = 100
with mido.open_input(devname) as port:
    for msg in port:
        print(msg)
        # dimmer.brightness = lastnonzero
        if msg.type == "note_on" and msg.note == 40:
            dimmer.brightness = 0
        if msg.type == "note_off" and msg.note == 40:
            dimmer.brightness = lastvalue * 2
        if msg.type == "control_change" and msg.control == 20:
            lastvalue = msg.value
            dimmer.brightness = lastvalue * 2


input()
