# midi.py
# always running midi listener
# based on dan's polyvoice



import amy
import tulip
import time

# Tulip defaults, 4 note polyphony on channel 1
# drum machine always on channel 10
PCM_PATCHES = 29
polyphony_map = {1:4, 10:10}
patch_map = {1:0}

# Our state
voices_for_channel = {}
note_for_voice = {}
voices_active = []
# Dict of per-channel booleans
in_sustain_dict = {}
# Dict of per-channel sets of notes
sustained_notes_dict = {}

def get_in_sustain(channel):
    global in_sustain_dict
    if channel not in in_sustain_dict:
        in_sustain_dict[channel] = False
    return in_sustain_dict[channel]

def set_in_sustain(channel, state):
    global in_sustain_dict
    in_sustain_dict[channel] = state

def get_sustained_notes_set(channel):
    global sustained_notes_dict
    if channel not in sustained_notes_dict:
        sustained_notes_dict[channel] = set()
    return sustained_notes_dict[channel]

def pitch_bend(channel, val):
    # get the active voices for this channel
    if channel not in voices_for_channel:
        return
    v_str = ""
    for v in voices_for_channel[channel]:
        if v in voices_active: v_str = v_str + "%d," % (v)
        if(len(v_str)):
            amy.send(voices=v_str[:-1], pitch_bend=val)

def sustain_pedal(channel, value):
    if value:
        set_in_sustain(channel, True)
    else:
        set_in_sustain(channel, False)
        sustained_notes = get_sustained_notes_set(channel)
        for midinote in sustained_notes:
            note_off(channel, midinote)
            sustained_notes.remove(midinote)  # Modifies the global.

# Get the voice for this chan/note 
def find_voice(channel, midinote):
    if channel not in voices_for_channel:
        return None

    for v in voices_for_channel[channel]:
        # Is this voice active already but also the existing note? that's ok
        if note_for_voice.get(v,None) == midinote:
            return v

        # Is this voice free? Use it
        if v not in voices_active:
            voices_active.append(v)
            note_for_voice[v] = midinote
            return v

    # couldn't find free voice. 
    # steal the earliest voice added
    for v in voices_active:
        if v in voices_for_channel[channel]:
            # move this stolen voice to the end
            voices_active.remove(v)
            voices_active.append(v)
            note_for_voice[v] = midinote
            return v

def note_on(channel, midinote, vel):
    # Drum channel is special
    voice = find_voice(channel, midinote)
    if voice is not None:
        if(channel == 10):
            amy.send(osc=voice, wave=amy.PCM, patch=midinote % PCM_PATCHES, vel=vel, freq=0)
        else:
            amy.send(voices="%d" % (voice), note=midinote, vel=vel)

def note_off(channel, midinote):  
    # Get the voice number for this midinote
    if get_in_sustain(channel):
        sustained_notes = get_sustained_notes_set(channel)
        sustained_notes.add(midinote)
        return
    for v in voices_for_channel[channel]:
        if note_for_voice.get(v,None) == midinote:
            # Remove it
            voices_active.remove(v)
            del note_for_voice[v]
            # Turn off the note
            if(channel == 10):
                amy.send(osc=v, vel=0)
            else:
                amy.send(voices='%d' % (v), vel=0)
            return

def update_channel(channel):
    time.sleep(0.1) # AMY queue will fill if not slept 
    vstr = ",".join([str(x) for x in voices_for_channel[channel]])
    amy.send(voices=vstr, load_patch=patch_map[channel])

def program_change(channel, patch):
    # update the map
    patch_map[channel] = patch
    update_channel(channel)

def midi_event_cb(x):
    """Callback that takes MIDI note on/off to create Note objects."""
    m = tulip.midi_in() 
    while m is not None and len(m) > 0:
        channel = (m[0] & 0x0F) + 1
        message = m[0] & 0xF0
        if message == 0x90:  # Note on.
            midinote = m[1]
            midivel = m[2]
            vel = midivel / 127.
            note_on(channel, midinote, vel)
        elif message == 0x80:  # Note off.
            midinote = m[1]
            note_off(channel, midinote)
        elif message == 0xc0:  # Program change
            program_change(channel, m[1])
        elif message == 0xe0:  # Pitch bend. m[2] is MSB, m[1] is LSB. 14 bits 
            pb_value = ((m[2] << 7) | (m[1])) - 8192 # -8192-8192, where 0 is nothing
            amy_value = float(pb_value)/(8192*6.0) # convert to -2 / +2 semitones
            amy.send(pitch_bend=amy_value)
        elif message == 0xb0 and m[1] == 0x40:
            sustain_pedal(channel, m[2])
    
        # Are there more events waiting?
        m = m[3:]
        if len(m) == 0:
            m = tulip.midi_in()

def setup_voices():
    amy.reset()
    v_counter = 0
    voices_for_channel[10] = list(range(110,120))
    for channel in polyphony_map.keys():
        if channel is not 10:
            voices_for_channel[channel] = list(range(v_counter, v_counter+polyphony_map[channel]))
            v_counter = v_counter + polyphony_map[channel]
            update_channel(channel)

def defer_setup(t):
    if(tulip.seq_ticks() > tulip.seq_ppq()):
        setup_voices()
        tulip.midi_callback(midi_event_cb)
        tulip.seq_remove_callback(defer_setup)

def music_map(channel, patch_number=None, voice_count=None):
    if voice_count is not None:
        polyphony_map[channel] = voice_count
        setup_voices()
    if patch_number is not None:
        patch_map[channel] = patch_number
        update_channel(channel)

def setup():
    # we can't setup on boot right away as we need to get the bleep going and the alles setup done, so wait on a callback
    tulip.seq_add_callback(defer_setup)


