'''
'''

import json
import mido
import os
from pyaudio import PyAudio
from samplestream import SampleStream
from fx import FX
from time import sleep

BACKEND = 'mido.backends.rtmidi'
CONFIG: dict = json.loads(open('config.json', 'r').read())
LP_NOTES_START = 0x24
CHANNEL = CONFIG['midi_channel']
HIT_COLOR = CONFIG['hit_color']
EMPTY_COLOR = CONFIG['empty_color']

def sysex_lightall(vel: int):
    return mido.Message.from_bytes([0xF0, 0x00, 0x20, 0x29, 0x02, 0x18, 0x0E, vel, 0xF7])

class Driver:
    audio = PyAudio()
    # launchpad input and output
    midiport: mido.ports.BaseIOPort
    # audio device number
    audiodev: int
    # map of notes (button IDs) to velocities (colors)
    colormap: dict[int, int]
    # map of notes (button IDs) to effect strings
    fxmap: dict[int, str]

    stream: SampleStream

    fx: FX

    def __init__(self):
        self.midiport = None

        print('\n' * 40)
        print('lpdriver.py\n')

        devs: list[str] = mido.get_output_names()
        for dev in devs:
            if dev.find(CONFIG['midi_device']) >= 0:
                self.midiport = mido.open_ioport(dev)
                print("Using MIDI device", dev)
                break
        
        if self.midiport is None:
            print("Error: could not find MIDI device")
            exit()

        # set launchpad layout to user 1 / drum rack
        layoutmsg = mido.Message.from_bytes([0xF0, 0x00, 0x20, 0x29, 0x02, 0x18, 0x22, 0x01, 0xF7])
        self.midiport.send(layoutmsg)
        # change all lights to the "empty" color
        self.midiport.send(sysex_lightall(EMPTY_COLOR))

        self.audiodev = -1
        num_outs = self.audio.get_device_count()
        for i in range(num_outs):
            name = self.audio.get_device_info_by_index(i)['name']
            if name.find(CONFIG['audio_device']) >= 0:
                self.audiodev = i
                print("Using audio device", name)
                break
        
        if self.audiodev < 0:
            print("Error: could not find audio output device")
            exit()

        print('\nPress CTRL+C to quit')

        self.stream = SampleStream(self.audio, self.audiodev)
        self.fx = FX(self.midiport, self.colormap)

        self.colormap = dict()
        self.fxmap = dict()
        for notestr, path in CONFIG['samples'].items():
            note_val = int(notestr)
            sample_dir = path[:path.rfind(os.path.sep)]
            self.stream.add(note_val, path)
            self.colormap[note_val] = CONFIG['dir_colors'][sample_dir]
            self.fxmap[note_val] = CONFIG['dir_effects'].get(sample_dir)
            self.midiport.send(mido.Message('note_on', channel=CHANNEL, note=note_val, velocity=self.colormap[note_val]))

    def run(self):
        try:
            while True:
                message = self.midiport.receive()
                if message.type == 'note_on' and message.velocity > 0:
                    self.stream.play(message.note)
                    self.midiport.send(mido.Message('note_on', channel=CHANNEL, note=message.note, velocity=HIT_COLOR))
                    self.fx.trigger(self.fxmap[message.note])
                elif message.type == 'note_on':
                    self.midiport.send(mido.Message('note_on', channel=CHANNEL, note=message.note, velocity=self.colormap.get(message.note, EMPTY_COLOR)))
        except KeyboardInterrupt as kbdint:
            pass

    def shut_down(self):
        # flush MIDI input messages
        while self.midiport.poll() is not None:
            pass
        # shut down effects thread
        self.fx.close()
        # shut off all lights
        self.midiport.send(sysex_lightall(0))
        self.midiport.close()
        self.audio.terminate()

if __name__ == "__main__":
    mido.set_backend(BACKEND)
    s = Driver()

    try:
        s.run()
    except Exception as e:
        print(e)
    s.shut_down()
