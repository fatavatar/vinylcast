#! /usr/bin/python3

import time
import pychromecast
import ffmpeg
import subprocess
import threading

CHROMECAST_NAME = 'Living Room speaker'
START_DELAY = 3
STOP_DELAY = 10
CAST_URL = 'icecast://source:controller@controller:8000/vinyl.ogg'
VOLUME_BOOST = '6dB'
SILENCE_THRESHOLD = '-45dB'
PLAY_URL = 'http://192.168.0.223:8000/vinyl.ogg'
VINYL_ICON = 'https://icon-icons.com/downloadimage.php?id=116200&root=1846/PNG/512/&file=recordplayer_116200.png'
playing = False

# FFMPEG COMMAND:
# ffmpeg -ac 2 -f alsa -i hw:2,0 -filter:a "volume=6dB" -ar 48000 -c:a flac -compression_level 
#       10 -f ogg -content_type 'application/ogg' -hide_banner 
#       -af silencedetect=n=-50dB:d=10 -loglevel info -nostats 
#       icecast://source:controller@controller:8000/vinyl.ogg

def get_chromecast():    
    while True:
        chromecasts, browser = pychromecast.get_chromecasts()
        #print(chromecasts)
        for cast in chromecasts:
            #print(cast)
            if cast.device.friendly_name == CHROMECAST_NAME:
                print("Found Chromecast")
                return cast
        print("Chromecast not detected...")
        time.sleep(5)
    
def start_stream():
    command = (
        ffmpeg
        .input('hw:2,0', f='alsa', ac=2, ar=48000, loglevel='info')
        .filter('silencedetect', n=SILENCE_THRESHOLD, d=1)
        .filter('volume', VOLUME_BOOST)
        .output(CAST_URL, f='ogg', 
            content_type='application/ogg', acodec="flac", compression_level=10)
        .compile()
    ) + ['-nostats'] + ['-hide_banner'] 
    # print(command)
    proc = subprocess.Popen(command, bufsize=1, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
        text=True, universal_newlines=True)
    return proc

def stop_cast(cast):
    global playing
    if playing:
        print("Stopping Cast")
        cast.wait()
        mc = cast.media_controller
        mc.stop()
        playing = False

def start_cast(cast):
    global playing
    if not playing:
        print("Starting Cast")
        cast.wait()
        mc = cast.media_controller
        # Tried stream_type="LIVE" - but seems to have adverse results
        mc.play_media(PLAY_URL, 'audio/ogg', title="Vinyl", thumb=VINYL_ICON )    
        mc.block_until_active()
        mc.play()
        playing = True
    

def main():
    cast = get_chromecast()
    stream = start_stream()
    stoptask = None
    starttask = None
    while True:
        try:
            stdout = stream.stdout.readline()
            # We set a small duration for silence detection, 1 second.
            # This is because we don't want little pops to cause us to turn on.
            # So we wait START_DELAY seconds before we turn on            
            if "silence_start" in stdout:
                if starttask is not None:
                    starttask.cancel()                
                    starttask = None
                print("Got Text: " + stdout, end='')
                if stoptask is None:
                    stoptask = threading.Timer(STOP_DELAY, stop_cast, (cast,))
                    stoptask.start()
            elif "silence_end" in stdout:
                if stoptask is not None:
                    stoptask.cancel()
                    stoptask = None
                print("Got Text: " + stdout, end='')
                if starttask is None:
                    starttask = threading.Timer(START_DELAY, start_cast, (cast,))
                    starttask.start()
        
        except Exception as e:
                print(e)

   

if __name__ == "__main__":
    main()