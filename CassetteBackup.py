fails = 1
while fails == 1:
    try:
        import subprocess
        import sys
        import pip
        import binascii
        import wave
        import numpy as np
        import time
        import soundfile as sf
        from pydub import AudioSegment
        from pydub.playback import play
        import pitch
        from scipy.io import wavfile
        from scipy import signal
        from threading import Thread
        import sounddevice as sd
        import os
        import playsound2

    except ModuleNotFoundError as error:
        missingModule = str(error)[17:-1]
        print("Module '" + missingModule + "' was not found on client machine installing module now")
        subprocess.check_call([sys.executable, "-m", "pip", "install", missingModule])

    else:
        fails = 0
# Variable declaration
loading_check = 0
fs = 8000


def loading_circle(loading_text):
    load = 0
    global loading_check
    while loading_check == 1:
        if load == 0:
            print(loading_text + "| ", end="\r")
            time.sleep(1)
            load += 1
        elif load == 1:
            print(loading_text + "\\ ", end="\r")
            time.sleep(1)
            load += 1
        elif load == 2:
            print(loading_text + "--", end="\r")
            time.sleep(1)
            load += 1
        elif load == 3:
            print(loading_text + "/ ", end="\r")
            time.sleep(1)
            load = 0


def start_line():
    mode = input("1:ENCODE\n2:DECODE\n")
    if mode == "1":
        encode_audio()
    elif mode == "2":
        decode_audio()


def encode_audio():
    global loading_check
    encode_in_file = input("What is the name of the file you wish to encode: ")
    # We read the file then encode it as binary
    a = open(encode_in_file, 'rb')
    c = a.read()
    b = bin(int(binascii.hexlify(c), 16))
    b = b.replace("b", "")
    print(b)
    # Produce the required tones for encoding and later decoding

    # Blanking interval tone used for bit separation \/
    volume = .25
    duration = .01  # in seconds
    t = np.arange(int(duration * fs)) / fs
    f = 10  # sine frequency, Hz
    samples = volume * np.sin(2 * np.pi * f * t)
    sf.write('0.wav', samples, fs, format="wav")

    # Low or 0 tone \/
    volume = .5  # range [0.0, 1.0]
    duration = .01  # in seconds
    f = 200  # sine frequency, Hz
    t = np.arange(int(duration * fs)) / fs
    samples = volume * np.sin(2 * np.pi * f * t)
    sf.write('200.wav', samples, fs, format="wav")

    # High or 1 tone \/
    volume = 1.0
    f = 800
    samples = volume * np.sin(2 * np.pi * f * t)
    sf.write('800.wav', samples, fs, format="wav")

    # SOF & EOF (Start and End of file detection tone \/
    duration = .05  # in seconds
    f = 100  # sine frequency, Hz
    t = np.arange(int(duration * fs)) / fs
    samples = volume * np.sin(2 * np.pi * f * t)
    sf.write('SOF.wav', samples, fs, format="wav")
    f = 150  # sine frequency, Hz
    t = np.arange(int(duration * fs)) / fs
    samples = volume * np.sin(2 * np.pi * f * t)
    sf.write('EOF.wav', samples, fs, format="wav")

    # We get ready for modulating the binary into sound
    modulated_sound, high_note = AudioSegment.empty(), AudioSegment.from_wav("800.wav")
    low_note, blank = AudioSegment.from_wav("200.wav"), AudioSegment.from_wav("0.wav")
    start_tone = AudioSegment.from_wav("SOF.wav")

    # Add 20 times blank for the start interval
    SOF_blanking_int, EOF_blanking_int, loading_check, end_tone = 10, 10, 1, AudioSegment.from_wav("EOF.wav")
    Thread(target=loading_circle, args=("Encoding Audio File: ",)).start()
    while SOF_blanking_int != 0:
        modulated_sound += blank
        SOF_blanking_int -= 1

    modulated_sound += start_tone  # Insert the SOF tone used to find the start of the file in decoding
    modulated_sound += blank
    for bit in b:
        if bit == '1':  # For every 1 in the binary list it inserts a high tone
            modulated_sound += high_note
            modulated_sound += blank
        else:  # We can safely assume that everything that isn't a 1 is a 0 so we insert a low tone
            modulated_sound += low_note
            modulated_sound += blank

    modulated_sound += end_tone  # Inserts the end tone used to stop the decode
    modulated_sound += blank
    while EOF_blanking_int != 0:
        modulated_sound += blank
        EOF_blanking_int -= 1
    loading_check = 0
    encoded_out_file = input("What would you like to call the exported file (do not include extension): ")
    encoded_out_file = encoded_out_file + ".wav"
    modulated_sound.export(encoded_out_file, format="wav")  # We export the sound file as the user chosen name
    read_duration = wave.open(encoded_out_file, "rb")
    # Reading the playtime of a audio file
    est_playtime = read_duration.getnframes() / float(read_duration.getframerate())
    read_duration.close()
    print("The binary contained in this file is: " + b[:10] + ". This can be used as debug information to make "
                                                              "sure the decoded file matches")
    # User is given a choice to start a playback of the encoded file to another machine and is given the time it
    # will take
    play_file = input("Would you like to play this file to another machine est: ~" + str(est_playtime)
                      + " seconds. (Y or N): ")
    if play_file.lower() == "y":
        # The file is played and the user is given time to make sure both systems are in a state ready to transfer
        input("Playback will proceed once you are ready press Enter.... ")
        playback_file = os.path.dirname(__file__) + "\\" + encoded_out_file
        loading_check = 1
        Thread(target=loading_circle, args=("Playing Audio File: ",)).start()
        playsound2.playsound(playback_file)
        loading_check = 0
        print("Encoded file has finished playback")
        # Once playback has finished the user is offered the ability to delete the encoded file in case it was
        # encoded just for a real time transfer
        keep_og = input("Would you like to keep the original file: (Y or N): ")
        if keep_og.lower() == "y":
            print("The original file has been kept")
        else:
            # The user is informed that the file should be closed from any applications
            print("Make sure the file is not currently open in anything")
            input("When ready press Enter.... ")
            try:
                os.remove(encoded_out_file)
            except PermissionError:  # The file wasn't deleted because it was open somewhere
                print("The file could not be removed because it was left open somewhere")

    else:  # The other option of not playing the file for another device
        print("The file will not be played for another device")
    try:
        os.remove("0.wav")
        os.remove("200.wav")
        os.remove("800.wav")
        os.remove("SOF.wav")
        os.remove("EOF.wav")
    except PermissionError:  # The file wasn't deleted because it was open somewhere
        print("The file could not be removed because it was left open somewhere")
    new_file = input("Would you like to start again with another file (Y or N): ")
    if new_file.lower() == "y":
        print("Starting again")
        start_line()
    else:
        pass


def decode_audio():
    global loading_check
    incoming_transfer, decode_in_file = 0, ''
    # SOF & EOF (Start and End of file detection tone \/
    volume = 1.0
    duration = .05  # in seconds
    f = 100  # sine frequency, Hz
    t = np.arange(int(duration * fs)) / fs
    samples = volume * np.sin(2 * np.pi * f * t)
    sf.write('SOF.wav', samples, fs, format="wav")
    decode_mode = input("Would you like to\n1: Decode a stored file\n2: prepare for an incoming transfer\n")
    if decode_mode == "1":
        incoming_transfer = 0
        print("You chose to decode a stored audio file")
        decode_in_file = input("Which file would you like to decode (This process can take a while): ")
    elif decode_mode == "2":
        incoming_transfer = 1
        print("You chose to decode an incoming transfer (This process is not real time and can take a while)")
        print("It is advised that this device begins recording at least 2-3 seconds before the transmitter begins the "
              "transfer (If less than 1 seconds simply put 1 seconds)")
        seconds = input("How long is the file you are expecting in seconds: ")
        seconds = int(seconds) + 2
        input("When ready press Enter.... ")
        # Setup for the recording of sound
        loading_check = 1
        Thread(target=loading_circle, args="Recording Incoming Data").start()
        duration = seconds
        recording = sd.rec(int(duration * fs),
                           samplerate=fs, channels=1,
                           dtype=np.int16)
        sd.wait()
        wavfile.write("cached_transfer.wav", fs, recording)
        decode_in_file = 'cached_transfer'
    else:
        print("You did not select an option")
        start_line()
    # read the sample to look for
    rate_snippet, snippet = wavfile.read("SOF.wav")
    snippet = np.array(snippet, dtype='float')

    # read the source
    rate, in_source = wavfile.read(decode_in_file + ".wav")
    in_source = np.array(in_source, dtype='float')

    # resample such that both signals are at the same sampling rate (if required)
    if rate != rate_snippet:
        num = int(np.round(rate * len(snippet) / rate_snippet))
        snippet = signal.resample(snippet, num)

    # compute the cross-correlation
    z = signal.correlate(in_source, snippet)

    peak = np.argmax(np.abs(z))
    end = peak / rate
    # Begin removing the SOF tone for easier reading
    with wave.open(decode_in_file + ".wav", 'rb') as f:
        duration = f.getnframes() / float(f.getframerate())
        source = AudioSegment.from_wav(decode_in_file + ".wav")
        # Actually cuts the SOF off the wav including the blanking time
        source = source[-((duration * 1000) - (end * 1000 + .01)):]
        source.export("SOF_cut.wav", format="wav")
        f.close()
    # Declare required variables for decoding
    x_start, x_end, reading, binary_read_list, load, read_list,  = 0, 25, 1, [], 0, 0
    binary_read_string, loading_check = '', 1
    Thread(target=loading_circle, args=("Reading Audio File: ",)).start()  # Begins the loading circle
    while reading != 0:  # Begin the decode
        try:  # Slice a section of audio knowing how long a tone is
            source = AudioSegment.from_wav("SOF_cut.wav")
            source = source[x_start:x_end]
            source.export("read_slice.wav", format="wav")
            # Used for next slice as it increased the slice time to later in the file
            x_start, x_end = x_start + 20, x_end + 20
            if 160 <= int(round(pitch.find_pitch("read_slice.wav"))) <= 290:  # Detect pitch for a 0 bit
                binary_read_list.append("0")
            elif 310 <= int(round(pitch.find_pitch("read_slice.wav"))) <= 410:  # Detect pitch for a 1 bit
                binary_read_list.append("1")
            elif int(round(pitch.find_pitch("read_slice.wav"))) < 160:
                reading = 0
                loading_check = 0
            else:
                pass
        except ValueError:  # Catch the end of the file using the ValueError generated by no audio present
            reading = 0
            loading_check = 0

    while read_list != len(binary_read_list):  # Convert the list of binary into one long string of binary
        binary_read_string += binary_read_list[(len(binary_read_list) - (read_list + 1))]
        read_list += 1
    binary_read_string = binary_read_string[::-1]  # Flip the string as it is read backwards
    print("Here is the decoded binary string which can be compared against the "
          "encoded one to ensure the file isn't damaged: " + binary_read_string[:10])
    # Shows the user a section of binary to compare to the encoded binary as a checksum

    n = int(binary_read_string, 2)  # Convert the binary string back into raw binary
    # User output file choice
    decode_out_file = input("What would you like to call the decoded file (Include extension): ")
    write_file = open(decode_out_file, 'wb')
    write_file.write(binascii.unhexlify('%x' % n))  # Its decoded and written back to a file form usable for the user
    write_file.close()
    if incoming_transfer == 0:
        keep_og = input("Do you wish to keep the encoded .wav file (Y or N): ")
        if keep_og.lower() == "y":
            print("The file will not be removed from your device")
        # The user is informed that the file should be closed from any applications
        else:
            print("Make sure the file is not currently open in anything")
            input("When ready press Enter.... ")
            try:
                os.remove(decode_out_file)
            except PermissionError:  # The file wasn't deleted because it was open somewhere
                print("The file could not be removed because it was left open somewhere")
    else:  # Asking the user if they wish to keep the file under a different name
        save_transfer = input("Do you wish to save the received .wav file (Y or N): ")
        if save_transfer.lower() == "y":
            save_name = input("What do you wish to call the file: ")
            source = AudioSegment.from_wav("cached_transfer.wav")
            source.export(save_name + ".wav", format="wav")
            try:
                os.remove('cached_transfer.wav')
            except PermissionError:
                print("Failed to remove the cached file you can safely remove it yourself")

        # Attempt to delete the temp file
        else:
            try:
                os.remove(decode_out_file)
            except PermissionError:  # The file wasn't deleted because it was open somewhere
                print("The file could not be removed because it was left open somewhere")
    try:
        os.remove("SOF.wav")
    except PermissionError:
        print("Failed to remove a temp file check if it was open somewhere")
    # Choice of encoding or decoding another file
    new_file = input("Would you like to start again with another file (Y or N): ")
    if new_file.lower() == "y":
        print("Starting again")
        start_line()
    else:
        pass


start_line()
