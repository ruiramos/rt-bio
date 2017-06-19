'''
    Python 2.7 example for gathering ECG and EDA data from bitalino and applying feature extraction

    Valtteri Wikstrom 2017
'''

import glob
import sys
import argparse

from bitalino import BITalino # pip install bitalino

from physiology import HeartRate, SkinConductance

from OSC import OSCClient, OSCMessage

parser = argparse.ArgumentParser()
parser.add_argument("--bitalino",
    default="15-65", help="The bitalino MAC address (ie, xx-xx)")
parser.add_argument("--osc_ip",
    default="localhost", help="The OSC server IP")
parser.add_argument("--osc_port",
    type=int, default=12345, help="The OSC server port")
parser.add_argument("--session",
    default="1", help="Session number (1-2)")
args = parser.parse_args()

#this is meant for OS X only
devices = glob.glob('/dev/tty.BITalino-{}'.format(args.bitalino))
try:
    print("opening port " + devices[0])
    device_address = devices[0]
except IndexError:
    raise Exception('No BITalino found using address {}'.format(args.bitalino))

chans = [1, 2] # ECG = 1, EDA = 2
fs = 100 # sampling rate
n_samples = 10 # how many samples to read from BITalino
session_id = int(args.session)

# Connect to BITalino
device = BITalino(device_address)

# Read BITalino version
print(device.version())

# Start Acquisition
device.start(fs, chans)

hr = HeartRate.HeartRate(fs, 32)
edr = SkinConductance.SkinConductance(fs, 20, 0.4, 20, 20)

osc_ip = args.osc_ip
osc_port = args.osc_port
print("connecting to osc server: {}:{}".format(osc_ip, osc_port))

client = OSCClient()
client.connect( (osc_ip, osc_port) )

ecg_ignore_beats = 5
ecg_last_rate = 0
ecg_rates = []

eda_ignore_values = 10
eda_reference = 0
eda_variation_threshold = 0

def handle_heartbeat(interval):
    global ecg_ignore_beats, ecg_last_rate

    if(ecg_ignore_beats > 0):
        # we're ignoring the first 5 readings
        ecg_ignore_beats -= 1
        return
    else:
        rate = 60 / interval

        if len(ecg_rates) > 4:
            # one last check: really off values filtered out
            variation = abs(ecg_last_rate - rate)
            if variation > ecg_last_rate * 1 or rate > 180 or rate < 40:
                print(" * Ignored beat reading {}".format(rate))
                return
            else:
                ecg_last_rate = rate

            ecg_rates[4] = rate

        else:
            # still collecting
            ecg_rates.append(rate)
            ecg_last_rate = rate

        # moving avg of the last values
        avg_rate = array_avg(ecg_rates)
        return avg_rate

def array_avg(rates):
    return sum(rates) / len(rates)

def handle_eda(samples):
    global eda_reference, eda_ignore_values

    eda_value = array_avg(samples)

    if(eda_reference == 0):
        # not sure about this here
        eda_reference = eda_value

    if(eda_ignore_values > 0):
        eda_ignore_values -= 1
        eda_reference = (eda_reference + eda_value) / 2
    else:
        eda_reference = 0.8 * eda_reference + 0.2 * eda_value

    return eda_value - eda_reference

def send_osc(client, path, args):
  try:
    msg = OSCMessage("/{}".format(path))
    msg.append(session_id)
    msg.append(args)
    client.send(msg)
  except:
    print("Couldnt send OSC message, server not running?")

try:
    while True:
        # Read samples
        in_samples = device.read(n_samples)

        ecg_samples = in_samples[:, 5]
        ibis = hr.add_data(ecg_samples)

        send_osc(client, "ecg", ecg_samples)

        for ibi in ibis:
            rate = handle_heartbeat(ibi)
            if(rate):
                rate = round(rate)
                print(" * Beat! Rate: {}".format(rate));
                send_osc(client, "beat", rate)

        eda_samples = in_samples[:, 6]
        variation = handle_eda(eda_samples)

        if(abs(variation) > eda_variation_threshold):
            variation = round(variation)
            val = array_avg(eda_samples)
            print(" * EDA change, variation: {}, value: {}".format(variation, val))
            send_osc(client, "eda", [variation, val])

        # send_osc(client, "eda", eda_samples)

#        edrs = edr.add_data(eda_samples)
#        for response in edrs:
#            amp = response[2]
#            print(" * EDA change, amplitude: {}".format(amp))
#            send_osc(client, "eda_change", amp)

except KeyboardInterrupt:
    # Stop acquisition
    device.stop()

    # Close connection
    device.close()
