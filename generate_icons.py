import os
import zlib
import struct
import math

def write_png(width, height, pixels, filename):
    # PNG signature
    png = bytearray([137, 80, 78, 71, 13, 10, 26, 10])
    
    # IHDR chunk
    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    png += struct.pack(">I", 13) + b"IHDR" + ihdr_data + struct.pack(">I", zlib.crc32(b"IHDR" + ihdr_data))
    
    # IDAT chunk
    idat_raw = bytearray()
    for y in range(height):
        idat_raw.append(0) # filter type 0 (none)
        for x in range(width):
            r, g, b = pixels[y][x]
            idat_raw.extend([r, g, b])
            
    idat_compressed = zlib.compress(idat_raw)
    png += struct.pack(">I", len(idat_compressed)) + b"IDAT" + idat_compressed + struct.pack(">I", zlib.crc32(b"IDAT" + idat_compressed))
    
    # IEND chunk
    png += struct.pack(">I", 0) + b"IEND" + struct.pack(">I", zlib.crc32(b"IEND"))
    
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, "wb") as f:
        f.write(png)

def make_cyber_pattern(width, height):
    cx, cy = width / 2.0, height / 2.0
    pixels = []
    for y in range(height):
        row = []
        for x in range(width):
            dx, dy = x - cx, y - cy
            dist = math.sqrt(dx*dx + dy*dy)
            
            # Dark futuristic grid background
            bg_r = 10
            bg_g = 5
            bg_b = 20
            
            # Add subtle tech grid lines
            if (x % max(1, width // 8) == 0) or (y % max(1, height // 8) == 0):
                bg_r, bg_g, bg_b = 20, 10, 40
                
            # Draw a beautiful glowing maze wall (outer ring)
            ring_radius = width * 0.4
            ring_thickness = max(2.0, width * 0.05)
            if abs(dist - ring_radius) < ring_thickness:
                # Magenta glow
                intensity = 1.0 - abs(dist - ring_radius) / ring_thickness
                r = int(bg_r + (255 - bg_r) * intensity)
                g = int(bg_g)
                b = int(bg_b + (255 - bg_b) * intensity)
            # Draw center glowing orb (cyan)
            elif dist < width * 0.2:
                intensity = 1.0 - dist / (width * 0.2)
                r = int(bg_r)
                g = int(bg_g + (255 - bg_g) * intensity)
                b = int(bg_b + (255 - bg_b) * intensity)
            # Some decorative diagonal cross lines inside the maze
            elif abs(abs(dx) - abs(dy)) < max(1, width * 0.03) and dist < ring_radius:
                r, g, b = 0, 200, 200
            else:
                r, g, b = bg_r, bg_g, bg_b
                
            row.append((max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b))))
        pixels.append(row)
    return pixels

# Generate icons of various sizes
sizes = [56, 112, 128]
print("Generating cyber-maze PNG icons...")
for s in sizes:
    pixels = make_cyber_pattern(s, s)
    write_png(s, s, pixels, f"public/assets/icon-{s}.png")
    print(f"Successfully generated public/assets/icon-{s}.png")

print("All icons successfully generated!")
