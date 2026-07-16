import math
import struct
import wave
import os
import subprocess

# Output configuration
SAMPLE_RATE = 44100  # 44.1 kHz standard audio
OUT_DIR = "public/audio"
os.makedirs(OUT_DIR, exist_ok=True)

def generate_wave(type_name, freq_func, duration, volume_func=None, stereo_pan_func=None):
    """
    Generates high-quality stereo audio sample buffer.
    freq_func: function(t) returning frequency at time t (0 to duration)
    volume_func: function(t) returning amplitude multiplier (0 to 1.0)
    stereo_pan_func: function(t) returning panning value (-1.0 for Left, 1.0 for Right, 0.0 for Center)
    """
    num_samples = int(SAMPLE_RATE * duration)
    left_channel = []
    right_channel = []
    
    phase = 0.0
    
    # Simple pseudo-random noise generator for transients (metallic hit or rumbles)
    noise_seed = 0x12345
    def get_noise():
        nonlocal noise_seed
        noise_seed = (1103515245 * noise_seed + 12345) & 0x7fffffff
        return (noise_seed / 1073741824.0) - 1.0

    for i in range(num_samples):
        t = i / SAMPLE_RATE
        
        # Get dynamic frequency
        freq = freq_func(t)
        
        # Accumulate phase to avoid discontinuity
        phase += 2.0 * math.pi * freq / SAMPLE_RATE
        
        # Generate raw waveform
        if type_name == 'sine':
            val = math.sin(phase)
        elif type_name == 'triangle':
            val = 2.0 * abs(2.0 * (phase / (2.0 * math.pi) - math.floor(phase / (2.0 * math.pi) + 0.5))) - 1.0
        elif type_name == 'square':
            val = 1.0 if math.sin(phase) >= 0 else -1.0
        elif type_name == 'sawtooth':
            val = 2.0 * (phase / (2.0 * math.pi) - math.floor(phase / (2.0 * math.pi) + 0.5))
        elif type_name == 'noise':
            val = get_noise()
        else:
            val = math.sin(phase)
            
        # Volume Envelope
        vol = 1.0
        if volume_func:
            vol = volume_func(t)
            
        # Apply volume
        val *= vol
        
        # Stereo Panning
        pan = 0.0  # Center
        if stereo_pan_func:
            pan = stereo_pan_func(t)
            
        # Constant power panning
        # Left channel multiplier: cos((pan + 1) * pi / 4)
        # Right channel multiplier: sin((pan + 1) * pi / 4)
        pan_angle = (pan + 1.0) * math.pi / 4.0
        left_val = val * math.cos(pan_angle)
        right_val = val * math.sin(pan_angle)
        
        left_channel.append(left_val)
        right_channel.append(right_val)
        
    return left_channel, right_channel

def apply_compression_and_normalization(left, right):
    """
    Applies high-quality dynamic range compression and brickwall limiting 
    to maximize the loudness to be extremely loud and punching without clipping.
    """
    # 1. Soft-kneel compressor / Limiter
    # Threshold = 0.5 (-6dB). Any amplitude above 0.5 gets compressed using a smooth tanh function
    # to pack maximum energy.
    threshold = 0.4
    compressed_left = []
    compressed_right = []
    
    for val in left:
        sign = 1.0 if val >= 0 else -1.0
        abs_val = abs(val)
        if abs_val > threshold:
            # Compress upper range softly
            compressed_val = threshold + (1.0 - threshold) * math.tanh((abs_val - threshold) / (1.0 - threshold))
            compressed_left.append(compressed_val * sign)
        else:
            compressed_left.append(val)
            
    for val in right:
        sign = 1.0 if val >= 0 else -1.0
        abs_val = abs(val)
        if abs_val > threshold:
            compressed_val = threshold + (1.0 - threshold) * math.tanh((abs_val - threshold) / (1.0 - threshold))
            compressed_right.append(compressed_val * sign)
        else:
            compressed_right.append(val)
            
    # 2. Normalize to exactly 0.99 peak amplitude for pristine digital mastery (extra loud!)
    max_val = 1e-5
    for l, r in zip(compressed_left, compressed_right):
        max_val = max(max_val, abs(l), abs(r))
        
    norm_factor = 0.99 / max_val
    normalized_left = [l * norm_factor for l in compressed_left]
    normalized_right = [r * norm_factor for r in compressed_right]
    
    return normalized_left, normalized_right

def save_wav(filename, left, right):
    """Saves standard 16-bit stereo WAV file."""
    wav_path = filename + ".wav"
    with wave.open(wav_path, "wb") as w:
        w.setnchannels(2)  # Stereo
        w.setsampwidth(2)  # 16-bit
        w.setframerate(SAMPLE_RATE)
        
        # Pack float values to 16-bit signed integers (-32768 to 32767)
        frames = []
        for l, r in zip(left, right):
            l_int = int(max(-32768, min(32767, l * 32767)))
            r_int = int(max(-32768, min(32767, r * 32767)))
            frames.append(struct.pack("<hh", l_int, r_int))
            
        w.writeframes(b"".join(frames))
    return wav_path

def convert_to_ogg(wav_path, ogg_name):
    """Converts the WAV file to extremely high quality OGG using FFmpeg."""
    ogg_path = os.path.join(OUT_DIR, ogg_name + ".ogg")
    # -y (overwrite), -c:a libvorbis (ogg vorbis codec), -q:a 8 (pristine sound quality ~256 kbps)
    cmd = ["ffmpeg", "-y", "-i", wav_path, "-c:a", "libvorbis", "-q:a", "8", ogg_path]
    try:
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        print(f"Successfully generated high-quality loud OGG: {ogg_path}")
    except subprocess.CalledProcessError as e:
        print(f"Failed to convert {wav_path} to OGG: {e}")
    finally:
        # Cleanup temporary WAV
        if os.path.exists(wav_path):
            os.remove(wav_path)

# ==========================================
# SOUND DESIGN RECIPES (CRISP, DEEP, ULTRA-LOUD)
# ==========================================

def make_start_sound():
    print("Generating 'start' sound...")
    # Dynamic pitch sweep: Exponentially rise from 330 Hz (E4) to 784 Hz (G5)
    def freq(t):
        return 330.0 * math.exp(t * 2.8)
        
    # Attack-Decay-Sustain-Release (ADSR) envelope
    def volume(t):
        if t < 0.05:  # Rapid punchy attack
            return t / 0.05
        else:  # Steady decay
            return max(0.0, 1.0 - (t - 0.05) / 0.3)
            
    # Spatial pan sweeping from left (-0.8) to right (+0.8)
    def pan(t):
        return -0.8 + (t / 0.35) * 1.6

    # Layer a sine oscillator and a triangle oscillator for a rich cyber resonance
    l1, r1 = generate_wave('triangle', freq, 0.35, volume, pan)
    l2, r2 = generate_wave('sine', lambda t: freq(t) * 1.01, 0.35, volume, pan) # Chorus detune
    
    l_mix = [x + y * 0.4 for x, y in zip(l1, l2)]
    r_mix = [x + y * 0.4 for x, y in zip(r1, r2)]
    
    l_final, r_final = apply_compression_and_normalization(l_mix, r_mix)
    wav = save_wav("start", l_final, r_final)
    convert_to_ogg(wav, "start")

def make_bounce_sound():
    print("Generating 'bounce' sound...")
    # Bounce is short, punchy, starting at 150 Hz sweeping down to 50 Hz
    def freq(t):
        return max(50.0, 150.0 - (t / 0.09) * 100.0)
        
    def volume(t):
        # Extremely fast attack, logarithmic rapid decay for heavy impact
        if t < 0.005:
            return t / 0.005
        else:
            return max(0.0, 1.0 - math.sqrt(t / 0.095))
            
    def pan(t):
        return -0.2  # Slightly left-centered

    # Sine for the warm bass, mixed with a transient click of noise
    l_sine, r_sine = generate_wave('sine', freq, 0.095, volume, pan)
    
    # Noise transient
    l_noise, r_noise = generate_wave('noise', lambda t: 1000, 0.015, lambda t: (1.0 - t/0.015) * 0.35, pan)
    
    # Mix
    l_mix = l_sine[:]
    r_mix = r_sine[:]
    for i in range(len(l_noise)):
        l_mix[i] += l_noise[i]
        r_mix[i] += r_noise[i]
        
    l_final, r_final = apply_compression_and_normalization(l_mix, r_mix)
    wav = save_wav("bounce", l_final, r_final)
    convert_to_ogg(wav, "bounce")

def make_gem_sound():
    print("Generating 'gem' sound...")
    # C-Major diamond sparkle chime: arpeggiated 4 notes staggered
    # C5 (523.25), E5 (659.25), G5 (783.99), C6 (1046.50)
    notes = [523.25, 659.25, 783.99, 1046.50]
    total_len = 0.35
    num_samples = int(SAMPLE_RATE * total_len)
    
    l_mix = [0.0] * num_samples
    r_mix = [0.0] * num_samples
    
    # Synthesize and superimpose each note with delays
    for idx, freq_val in enumerate(notes):
        delay = idx * 0.045
        duration = 0.16
        
        # Triangle + sine for beautiful high crystal ring
        l_note, r_note = generate_wave(
            'triangle', 
            lambda t: freq_val, 
            duration, 
            volume_func=lambda t: max(0.0, 1.0 - t/duration) * 0.5,
            stereo_pan_func=lambda t: -0.6 + (idx / 3.0) * 1.2  # Staggered pan
        )
        
        # Add to main buffer with offset
        start_sample = int(delay * SAMPLE_RATE)
        for i in range(len(l_note)):
            if start_sample + i < num_samples:
                l_mix[start_sample + i] += l_note[i]
                r_mix[start_sample + i] += r_note[i]
                
    l_final, r_final = apply_compression_and_normalization(l_mix, r_mix)
    wav = save_wav("gem", l_final, r_final)
    convert_to_ogg(wav, "gem")

def make_fall_sound():
    print("Generating 'fall' sound...")
    # Deep sweeping fall sawtooth. Sweeps from 220 Hz down to 25 Hz.
    def freq(t):
        return max(25.0, 220.0 * (1.0 - t / 0.55))
        
    def volume(t):
        return max(0.0, 1.0 - t / 0.55)
        
    def pan(t):
        # Rotates in circle panning back and forth
        return math.sin(t * 12.0) * 0.6

    l_saw, r_saw = generate_wave('sawtooth', freq, 0.55, volume, pan)
    l_sub, r_sub = generate_wave('sine', lambda t: freq(t)*0.5, 0.55, lambda t: volume(t)*0.75, pan) # Sub bass layer
    
    l_mix = [x + y for x, y in zip(l_saw, l_sub)]
    r_mix = [x + y for x, y in zip(r_saw, r_sub)]
    
    l_final, r_final = apply_compression_and_normalization(l_mix, r_mix)
    wav = save_wav("fall", l_final, r_final)
    convert_to_ogg(wav, "fall")

def make_portal_sound():
    print("Generating 'portal' sound...")
    # Pulse resonance laser sweep 440 Hz -> 980 Hz
    def freq(t):
        return 440.0 + (t / 0.28) * 540.0
        
    def volume(t):
        # LFO modulation for vibrating cyber portal effect
        lfo = 0.7 + 0.3 * math.sin(t * 40.0)
        envelope = max(0.0, 1.0 - t / 0.28)
        return envelope * lfo
        
    def pan(t):
        return math.cos(t * 15.0) * 0.7

    l_sq, r_sq = generate_wave('square', freq, 0.28, volume, pan)
    l_final, r_final = apply_compression_and_normalization(l_sq, r_sq)
    wav = save_wav("portal", l_final, r_final)
    convert_to_ogg(wav, "portal")

def make_win_sound():
    print("Generating 'win' sound...")
    # Triumphant chord: Major chord (C4, E4, G4, C5, E5)
    freqs = [261.63, 329.63, 392.00, 523.25, 659.25]
    total_len = 0.6
    num_samples = int(SAMPLE_RATE * total_len)
    
    l_mix = [0.0] * num_samples
    r_mix = [0.0] * num_samples
    
    for idx, f in enumerate(freqs):
        delay = idx * 0.05
        duration = 0.4
        
        # Sine + triangle for a lush rich harmonic chord
        l_chord, r_chord = generate_wave(
            'triangle', 
            lambda t: f, 
            duration, 
            volume_func=lambda t: (1.0 - t/duration) * 0.4,
            stereo_pan_func=lambda t: -0.7 + (idx / 4.0) * 1.4
        )
        
        start_sample = int(delay * SAMPLE_RATE)
        for i in range(len(l_chord)):
            if start_sample + i < num_samples:
                l_mix[start_sample + i] += l_chord[i]
                r_mix[start_sample + i] += r_chord[i]
                
    l_final, r_final = apply_compression_and_normalization(l_mix, r_mix)
    wav = save_wav("win", l_final, r_final)
    convert_to_ogg(wav, "win")

# Run all generator recipes
if __name__ == "__main__":
    make_start_sound()
    make_bounce_sound()
    make_gem_sound()
    make_fall_sound()
    make_portal_sound()
    make_win_sound()
    print("--- ALL HIGH-QUALITY SOUNDS COMPLETED ---")
