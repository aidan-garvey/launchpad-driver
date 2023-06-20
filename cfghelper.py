'''
'''

import json
import mido
import os
from pyaudio import PyAudio

CONFIG: dict = json.loads(open('config.json', 'r').read())

midiport = None

def sysex_lightall(vel: int):
    return mido.Message.from_bytes([0xF0, 0x00, 0x20, 0x29, 0x02, 0x18, 0x0E, vel, 0xF7])

def quit():
    # allow user to save changes
    choice = ''
    while choice != 'Y' and choice != 'N':
        choice = input("Save changes? [Y/N]").upper()[:1]
    if choice == 'Y':
        f = open('config.json', 'w')
        f.write(json.dumps(CONFIG))
    
    # clear buttons
    midiport.send(sysex_lightall(0))

    # flush MIDI inputs
    while midiport.poll() is not None:
        pass

    midiport.close()

    exit(0)

def prompt(opts: dict[int, str], last) -> int:
    print("\nEnter one of the following options:")
    for num, desc in opts.items():
        print(f'{num}) {desc}')
    print(f'0) {last}')
    choice = -1
    while choice not in opts.keys() and choice != 0:
        try:
            choice = int(input('\n> '))
        except ValueError:
            choice = -1
            print(f'Invalid value, try again:')
    return choice

def cfg_midi_dev():
    devs: list[str] = mido.get_output_names()
    opts = dict()
    for i in range(len(devs)):
        opts[i + 1] = devs[i]
    choice = prompt(opts, "cancel")
    if choice > 0:
        CONFIG['midi_device'] = opts[choice]
    print(f'Using MIDI device: {CONFIG["midi_device"]}')

def cfg_audio_dev():
    audio = PyAudio()
    opts = dict()
    for i in range(audio.get_device_count()):
        name = audio.get_device_info_by_index(i)['name']
        opts[i + 1] = name
    choice = prompt(opts, "cancel")
    if choice > 0:
        CONFIG['audio_device'] = opts[choice]
    print(f'Using audio device: {CONFIG["audio_device"]}')

def cfg_midi_channel():
    channel = 0
    while channel < 1 or channel > 16:
        try:
            channel = int(input("Enter MIDI channel for your controller (1-16): "))
        except ValueError:
            channel = 0
    CONFIG['midi_channel'] = channel - 1
    print(f'Using MIDI channel {CONFIG["midi_channel"] + 1}')

def menu_samples():
    # initialize button colors, save a map of notes to samples (reverse of config)
    for note_val, path in CONFIG['samples'].items():
        sample_dir = path[:path.rfind(os.path.sep)]
        midiport.send(mido.Message('note_on', channel=CONFIG['midi_channel'], note=int(note_val), velocity=CONFIG['dir_colors'][sample_dir]))

    print("Press a button on the controller to assign a sample, press one of the arrow buttons to go back")

    # let user assign samples
    while True:
        message = midiport.receive()
        if message.type == 'note_on' and message.velocity > 0:
            notestr = str(message.note)
            midiport.send(mido.Message('note_on', channel=message.channel, note=message.note, velocity=12))
            opts = dict()
            curr = 1
            for path, _, files in os.walk('samples'):
                for f in files:
                    opts[curr] = os.path.join(path[path.find(os.path.sep) + 1:], f)
                    curr += 1
            choice = prompt(opts, f"use current ({CONFIG['samples'].get(notestr, 'none')})")

            if choice > 0:
                name = opts[choice]
                dirname = name[:name.rfind(os.path.sep)]

                print("Using", name, "from", dirname)

                CONFIG['samples'][notestr] = name
                midiport.send(mido.Message('note_on', channel=message.channel, note=message.note, velocity=CONFIG['dir_colors'].get(dirname, 40)))

            elif CONFIG['samples'].get(notestr, None) is None:
                midiport.send(mido.Message('note_on', channel=message.channel, note=message.note, velocity=0))

            else:
                name = CONFIG['samples'][notestr]
                dirname = name[:name.rfind(os.path.sep)]
                midiport.send(mido.Message('note_on', channel=message.channel, note=message.note, velocity=CONFIG['dir_colors'].get(dirname, 40)))

            print("Press a button on the controller to assign a sample, press one of the arrow buttons to go back")

        elif message.is_cc():
            break

    # flush midi inputs
    while midiport.poll() is not None:
        pass

def menu_colors():
    pass

if __name__ == "__main__":
    print('\n\n\n\n')

    mido.set_backend('mido.backends.rtmidi')

    # startup: allow user to select a MIDI and audio device
    print("Configuration helper")
    choice = prompt({1: f'use saved MIDI controller ({CONFIG["midi_device"]})',
                     2: 'choose a different MIDI controller'}, "exit")
    
    if choice == 0:
        quit()
    elif choice == 2:
        cfg_midi_dev()

    midiport = mido.open_ioport(CONFIG['midi_device'])

    choice = prompt({1: f'use saved audio device ({CONFIG["audio_device"]})',
                     2: 'choose a different audio device'}, "exit")

    if choice == 0:
        quit()
    elif choice == 2:
        cfg_audio_dev()

    choice = prompt({1: f'use saved MIDI channel ({CONFIG["midi_channel"] + 1})',
                     2: 'choose another channel'}, "exit")
    if choice == 0:
        quit()
    elif choice == 2:
        cfg_midi_channel()

    while choice != 0:
        choice = prompt({1: 'assign samples', 2: 'assign colors'}, "exit")
        if choice == 1:
            menu_samples()
        elif choice == 2:
            menu_colors()
    
    quit()
