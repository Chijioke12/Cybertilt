import os
import sys

def strip_sim():
    svelte_path = "src/App.svelte"
    if not os.path.exists(svelte_path):
        print("Error: src/App.svelte not found")
        return False

    with open(svelte_path, "r", encoding="utf-8") as f:
        content = f.read()

    start_tag = "{#if isDeviceBuild}"
    start_idx = content.find(start_tag)
    if start_idx == -1:
        print("Error: Could not find start tag '{#if isDeviceBuild}' in App.svelte")
        return False

    # Robust Svelte block parser to find the top-level {:else} and {/if} matching {#if isDeviceBuild}
    depth = 1
    idx = start_idx + len(start_tag)
    middle_idx = -1
    end_idx = -1
    n = len(content)
    while idx < n:
        nxt = content.find('{', idx)
        if nxt == -1:
            break
        if content.startswith('{#if', nxt) or content.startswith('{#each', nxt) or content.startswith('{#await', nxt):
            depth += 1
        elif content.startswith('{/if}', nxt) or content.startswith('{/each}', nxt) or content.startswith('{/await}', nxt):
            depth -= 1
            if depth == 0:
                end_idx = nxt
                break
        elif content.startswith('{:else', nxt):
            if depth == 1:
                middle_idx = nxt
        idx = nxt + 1

    if middle_idx == -1:
        print("Error: Could not find matching top-level '{:else}' in App.svelte")
        return False
    if end_idx == -1:
        print("Error: Could not find matching top-level '{/if}' in App.svelte")
        return False
        
    style_idx = content.find("<style>")
    if style_idx == -1:
        print("Error: Could not find <style> tag in App.svelte")
        return False
        
    # Extract the device-only HTML template
    device_html = content[start_idx + len(start_tag):middle_idx].strip()
    
    # Create the new stripped App.svelte content
    new_content = content[:start_idx] + "\n" + device_html + "\n\n" + content[style_idx:]
    
    # Backup the original
    bak_path = svelte_path + ".bak"
    with open(bak_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Backed up original file to {bak_path}")
        
    # Write the stripped version
    with open(svelte_path, "w", encoding="utf-8") as f:
        f.write(new_content)
    print("Successfully stripped simulator UI from src/App.svelte!")
    return True

def restore_sim():
    svelte_path = "src/App.svelte"
    bak_path = svelte_path + ".bak"
    if os.path.exists(bak_path):
        os.replace(bak_path, svelte_path)
        print("Successfully restored src/App.svelte from backup.")
        return True
    else:
        print("Warning: No backup file found to restore.")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "restore":
        restore_sim()
    else:
        strip_sim()
