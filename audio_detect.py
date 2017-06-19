#! /usr/bin/env python

# Use pyaudio to open the microphone and run aubio.pitch on the stream of
# incoming samples. If a filename is given as the first argument, it will
# record 5 seconds of audio to this location. Otherwise, the script will
# run until Ctrl+C is pressed.

# Examples:
#    $ ./python/demos/demo_pyaudio.py
#    $ ./python/demos/demo_pyaudio.py /tmp/recording.wav

import pyaudio
import sys
import numpy as np
from aubio import tempo, source
from OSC import OSCClient, OSCMessage

# initialise pyaudio
p = pyaudio.PyAudio()

print("connecting to osc server");
osc_ip = "localhost"
osc_port = 12345

client = OSCClient()
client.connect( (osc_ip, osc_port) )

# open stream
buffer_size = 1024
pyaudio_format = pyaudio.paFloat32
n_channels = 1
samplerate = 44100
stream = p.open(format=pyaudio_format,
        channels=n_channels,
        rate=samplerate,
        input=True,
        frames_per_buffer=buffer_size)

total_frames = 0

# setup tempo
win_s = 1024 * 2 # fft size
hop_s = win_s // 2 # hop size
tempo_o = tempo("default", win_s, hop_s, samplerate)

print("*** starting recording")
while True:
    try:
        audiobuffer = stream.read(buffer_size)
        signal = np.fromstring(audiobuffer, dtype=np.float32)

        is_beat = tempo_o(signal)

        if is_beat and is_beat[0] > 0:
            print('tick')
            try:
                msg = OSCMessage("/tick")
                client.send(msg)
            except:
                print("Couldnt send OSC message, server not running?")

        total_frames += buffer_size

    except KeyboardInterrupt:
        print("*** Ctrl+C pressed, exiting")
        break

print("*** done recording")
stream.stop_stream()
stream.close()
p.terminate()
