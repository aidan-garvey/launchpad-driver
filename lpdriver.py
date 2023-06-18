'''
'''

import json
import mido
from pyaudio import PyAudio
from samplestream import SampleStream

BACKEND = 'mido.backends.rtmidi'
CONFIG: dict = json.loads(open('config.json', 'r').read())

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

        devs: list[str] = mido.get_output_names()
        for dev in devs:
            if dev.find(CONFIG['midi_device']) >= 0:
                self.midiport = mido.open_ioport(dev)
                break
        
        if self.midiport is None:
            print("Error: could not find MIDI device")
            exit()

        self.audiodev = -1
        num_outs = self.audio.get_device_count()
        for i in range(num_outs):
            name = self.audio.get_device_info_by_index(i)['name']
            if name.find(CONFIG['audio_device']) >= 0:
                self.audiodev = i
                break
        
        if self.audiodev < 0:
            print("Error: could not find audio output device")
            exit()

        self.stream = SampleStream(self.audio, self.audiodev)


if __name__ == "__main__":
    mido.set_backend(BACKEND)
    s = Driver()

    try:
        s.run()
    except Exception as e:
        print(e)
    s.shut_down()
