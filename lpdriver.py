'''
'''

import json
import mido
from pyaudio import PyAudio
from samplestream import SampleStream
from time import sleep

BACKEND = 'mido.backends.rtmidi'
CONFIG: dict = json.loads(open('config.json', 'r').read())
LP_NOTES_START = 0x24

class Driver:
    audio = PyAudio()
    # launchpad input and output
    midiport: mido.ports.BaseIOPort
    # audio device number
    audiodev: int

    stream: SampleStream

    online: bool

    def __init__(self):
        self.online = True
        self.midiport = None

        print('\n' * 40)

        devs: list[str] = mido.get_output_names()
        for dev in devs:
            if dev.find(CONFIG['midi_device']) >= 0:
                self.midiport = mido.open_ioport(dev)
                print("Using midi device", dev)
                break
        
        if self.midiport is None:
            print("Error: could not find MIDI device")
            exit()

        # set launchpad layout to user 1 / drum rack
        layoutmsg = mido.Message.from_bytes([0xF0, 0x0, 0x20, 0x29, 0x02, 0x18, 0x22, 0x01, 0xF7])
        self.midiport.send(layoutmsg)

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

        self.stream = SampleStream(self.audio, self.audiodev)

        samples = CONFIG['samples']
        for i in range(len(samples)):
            self.stream.add(i + LP_NOTES_START, samples[i])

    def run(self):
        self.online = True
        while self.online:
            message = self.midiport.receive()
            if message.type == 'note_on':
                self.stream.play(message.note)

    def shut_down(self):
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
