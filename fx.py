'''
'''

import mido
import multiprocessing as mp
import queue
import time
import json

class FX:
    port: mido.ports.BaseIOPort
    colormap: dict[int, int]

    worker: mp.Process
    jobs: mp.Queue

    config = json.loads(open('config.json', 'r').read())
    channel = config['midi_channel']
    empty_color = config['empty_color']

    def __init__(self, midiport, colormap):
        self.port = midiport
        self.jobs = mp.Queue()
        self.worker = mp.Process(target=self.workerfn)
        self.colormap = colormap.copy()

        self.worker.start()

    def trigger(self, effect):
        if effect is not None:
            # visual effects aren't as important as sound, so if we can't add the effect just abort
            try:
                self.jobs.put(effect)
            except Exception as e:
                print(f'Error in FX.trigger: {e}')
    
    def close(self):
        self.jobs.close()
        self.jobs.join_thread()
        self.worker.join()

    def sysex_lightall(self, vel: int):
        return mido.Message.from_bytes([0xF0, 0x00, 0x20, 0x29, 0x02, 0x18, 0x0E, vel, 0xF7])

    def strobe(self):
        self.port.send(self.sysex_lightall(3))
        time.sleep(0.04)
        self.port.send(self.sysex_lightall(0))
        time.sleep(0.04)
        self.port.send(self.sysex_lightall(3))
        time.sleep(0.04)
        self.port.send(self.sysex_lightall(self.empty_color))
        for n, v in self.colormap.items():
            self.port.send(mido.Message('note_on', channel=self.channel, note=n, velocity=v))

    def handle_job(self, job):
        if job == 'strobe':
            self.strobe()

    def workerfn(self):
        while True:
            try:
                job = self.jobs.get(block=True, timeout=1)
                self.handle_job(job)
            # timeout due to empty queue: try again
            except queue.Empty:
                pass
            # exception due to queue closed: terminate loop
            except Exception as e:
                print(f'Error in FX.workerfn: {e}')
