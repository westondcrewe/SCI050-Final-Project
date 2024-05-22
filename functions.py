import time
import random
import math
import wave
import copy
import colorsys
import csaudio
from csaudio import *
import numpy as np
from matplotlib import pyplot as plt
from PIL import Image
wave.big_endian = 0 

##### VISUAL ######
def plot_wav(samples):
    # source: https://matplotlib.org/stable/gallery/lines_bars_and_markers/simple_plot.html#sphx-glr-gallery-lines-bars-and-markers-simple-plot-py
    fig, ax = plt.subplots()
    ax.plot(range(len(samples)), samples)

    ax.set(xlabel='sample', ylabel='value',
       title='WAV File Visualization of Value by Sample')
    ax.grid()

    fig.savefig("test.png")
    plt.show()
    return

##### IMAGE HANDLING #####
def getRGB(filename):
    """ reads a png or jpg file like 'flag.jpg' (a string)
        returns the pixels as a list-of-lists-of-lists
        this is accessible, but not fast: Use small images!
    """
    original = Image.open(filename)     # open the image
    print(f"Reading image from '{filename}':")
    print(f"  Format: {original.format}\n  Original Size: {original.size}\n  Mode: {original.mode}")
    max_dim = max(original.size)
    print(max_dim)
    MAX_DIMENSION = 2400   # edit this to allow larger images
    scale = max_dim/MAX_DIMENSION
    if scale > 1.0:
        new_size = tuple([round(x/scale) for x in original.size])
        print(f"WARNING:  New size is {new_size}")
        original = original.resize(new_size)
    else:
        print(f"Keeping original size of {original.size}")
        
    WIDTH, HEIGHT = original.size
    px = original.load()
    PIXEL_LIST = []
    for r in range(HEIGHT):
        row = []
        for c in range(WIDTH):
            row.append( px[c,r][:3] )
        PIXEL_LIST.append( row )
    return PIXEL_LIST

def saveRGB( PX, filename ):
    """ saves a list-of-lists-of-lists of rgb pixels (PX) where
        len(PX) == the # of rows
        len(PX[0]) == the # of columns
        len(PX[0][0]) should be 3 (rgb)
    """
    boxed_pixels = PX
    print( 'Starting to save', filename, '...' )
    H = len(PX)
    W = len(PX[0])
    im = Image.new("RGB", (W, H), "black")
    px = im.load()
    for r in range(H):
        for c in range(W):
            bp = boxed_pixels[r][c]
            t = tuple(bp)
            px[c,r] = t
    im.save( filename )
    time.sleep(0.42)   # give the filesystem some time...
    print( filename, "saved." )    

##### AUDIO-MESSAGE HANDLING ######
def sampleToMessage(samples):
    '''takes list of audio samples and converts the ints into binary values, 
        such that they may be easily embedded within an image using steganography
    '''
    #loop through samples
    #for each sample: grab value, if negative make positive, convert to bits, pad to 16 (2 bytes per sample)
    binaryAudioMessage = ""
    for samp in samples:
        if samp < 0:
            samp += 65536
        elif samp == 0:
            samp += 1
        binary = bin(samp)[2:]
        nbits = len(binary)    # to make sure we have 16 bits...
        binary = '0'*(16-nbits) + binary
        binaryAudioMessage += binary
    binaryAudioMessage += '0000000000000000000000000000000000000000000000000000000000000000'
    return binaryAudioMessage

def messageToSample(binaryMessage):
    '''takes a binary message and converts into audio sample data
        by converting every chunk of 16 bits (2 bytes) into its integer value, 
        and storing these values in a list
    '''
    #loop through 16 bit chunks of binaryMessage
    #for every 2 bytes: convert to ints, if out of range make negative, add to sample[]
    sample = []
    for bit_pointer in range(0, len(binaryMessage), 16):
        sample_bits = binaryMessage[bit_pointer:bit_pointer+16]
        sample_value = int(sample_bits, 2)
        if sample_value > 32767:
            sample_value -= 65536
        sample.append(sample_value)
    return sample

###### AUDIO TO IMAGE ######
def steganographize( image_rgb, binaryMessage ):
    """Embeds a message in an image's RGB data"""
    
    num_rows = len(image_rgb) 
    num_cols = len(image_rgb[0])
    print(f"There are {num_rows} rows and {num_cols} columns\n")

    ml = len(binaryMessage)
    available = num_rows*num_cols*3
    print(f"Message in binary is {binaryMessage} (with {ml//3} full pixels and {ml%3} extra values)")
    print(f"This image has {available} pixels\n")
    
    if ml > available:
        print(f"There is not enough space to encode your message here...")
        return 42
    
    new_rgb = copy.deepcopy(image_rgb)

    bi = 0    # our "bit index"
    for row in range(num_rows):
        print(f"row is {row}")
        for col in range(num_cols):
            print(f"col is {col}")

            r, g, b = image_rgb[row][col]  

            # for each channel, must check if bit index has hit end of message
            if bi == ml-1:
                return new_rgb
            # not at end of message, must propely change LSB to match message bit
            oldr = r
            if bin(r)[-1] != binaryMessage[bi]:
                if r%2==0:
                    r += 1
                else:
                    r -= 1
            print(f"Row {row}: Column{col}   Red new {r}    Red old {oldr}")

            bi += 1
            if bi == ml-1: 
                new_rgb[row][col] = (r,g,b)
                return new_rgb  
            if bin(g)[-1] != binaryMessage[bi]:
                if g%2==0:
                    g += 1
                else:
                    g -= 1

            bi += 1
            if bi == ml-1:
                new_rgb[row][col] = (r,g,b)
                return new_rgb
            if bin(b)[-1] != binaryMessage[bi]:
                if b%2==0:
                    b += 1
                else:
                    b -= 1

            bi += 1
            # Then, assign back to the new_rgb:  new_rgb[row][col] = (r,g,b)
            new_rgb[row][col] = (r,g,b)
            
    return new_rgb

    #return binaryMessage

##### IMAGE TO AUDIO ######
def desteganographize(image_rgb):
    """Extracts a message hidden in an image's RGB data"""
    num_rows = len(image_rgb) 
    num_cols = len(image_rgb[0])
    print(f"There are {num_rows} rows and {num_cols} columns\n")
    sub = ""        # current 16-bit chunk of whole message
    message = ""    # full binary message
    eof_check = ""
    
    # for each channel of each pixel, grab LSB
    for row in range(num_rows):
        #print(f"row is {row}")
        for col in range(num_cols):
            pix = image_rgb[row][col]
            for channel in pix:
                #print(type(bin(channel)))
                #print(channel)
                binary = bin(channel)   
                LSB = binary[-1]
                sub += LSB
                eof_check += LSB
                # if sub is 16, we must add it to the message and either return (if EOF) or set to empty string
                if len(sub) == 16: # when sub == 16, eof_check must be either 16 or 32                      
                    message += sub
                    if len(eof_check) == 32:
                        if eof_check == '00000000000000000000000000000000':
                            return message
                        else:
                            sub = ''
                            eof_check = ''
                    else: # len(sub) will still be 16 here
                        sub = ''
    