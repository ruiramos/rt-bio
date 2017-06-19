from OSC import OSCServer
import sys
from time import sleep

server = OSCServer( ("localhost", 7110) )
server.timeout = 0
run = True

# this method of reporting timeouts only works by convention
# that before calling handle_request() field .timed_out is
# set to False
def handle_timeout(self):
    self.timed_out = True

# funny python's way to add a method to an instance of a class
import types
server.handle_timeout = types.MethodType(handle_timeout, server)

def ecg_callback(path, tags, args, source):
  print ("ECG data:", args)

def eda_callback(path, tags, args, source):
  print ("EDA data:", args)

def beat_callback(path, tags, args, source):
  print ("* Beat! Heart rate::", args)

server.addMsgHandler( "/beat", beat_callback )
server.addMsgHandler( "/ecg", ecg_callback )
server.addMsgHandler( "/eda", eda_callback )
#server.addMsgHandler( "/user/4", user_callback )
#server.addMsgHandler( "/quit", quit_callback )

# user script that's called by the game engine every frame
def each_frame():
    # clear timed_out flag
    server.timed_out = False
    # handle all pending requests then return
    while not server.timed_out:
        server.handle_request()

# simulate a "game engine"
while run:
    # do the game stuff:
    sleep(1)
    # call user script
    each_frame()

server.close()

