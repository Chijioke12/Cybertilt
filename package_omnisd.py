import os
import zipfile
import json

def zip_directory(folder_path, zip_file):
    # Zip the contents of the folder, but not the folder itself
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            file_path = os.path.join(root, file)
            # Find the relative path of the file to preserve the directory structure
            relative_path = os.path.relpath(file_path, folder_path)
            zip_file.write(file_path, relative_path)

def main():
    print("Starting OmniSD packaging process...")
    
    dist_dir = "dist"
    if not os.path.exists(dist_dir):
        print(f"Error: {dist_dir} directory does not exist. Please run Vite build first.")
        return
        
    # 1. Create and write manifest.webapp to dist directory
    manifest_content = {
        "version": "1.0.0",
        "name": "CyberTilt 3D",
        "description": "3D Balance Labyrinth for KaiOS",
        "launch_path": "/index.html",
        "icons": {
            "56": "/assets/icon-56.png",
            "112": "/assets/icon-112.png",
            "128": "/assets/icon-128.png"
        },
        "developer": {
            "name": "KaiOS Developer",
            "url": "http://kaiostech.com"
        },
        "origin": "app://cybertilt",
        "type": "web",
        "fullscreen": "true",
        "permissions": {},
        "locales": {
            "en-US": {
                "name": "CyberTilt 3D",
                "description": "3D Balance Labyrinth for KaiOS"
            }
        },
        "default_locale": "en"
    }
    
    manifest_path = os.path.join(dist_dir, "manifest.webapp")
    with open(manifest_path, "w") as f:
        json.dump(manifest_content, f, indent=2)
    print(f"Created {manifest_path}")

    # 2. Package dist contents into application.zip
    app_zip_path = "application.zip"
    print(f"Creating {app_zip_path} from {dist_dir}...")
    with zipfile.ZipFile(app_zip_path, 'w', zipfile.ZIP_DEFLATED) as zip_app:
        zip_directory(dist_dir, zip_app)
    print(f"Successfully packaged {app_zip_path}")

    # 3. Create update.webapp (empty file)
    update_webapp_path = "update.webapp"
    with open(update_webapp_path, "w") as f:
        f.write("")
    print(f"Created {update_webapp_path}")

    # 4. Create metadata.json for OmniSD
    metadata_content = {
        "version": 1,
        "manifestURL": "app://cybertilt/manifest.webapp"
    }
    metadata_path = "metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata_content, f, indent=2)
    print(f"Created {metadata_path}")

    # 5. Package all three into the final OmniSD zip package
    final_zip_name = "cybertilt-omnisd.zip"
    print(f"Creating final OmniSD package: {final_zip_name}...")
    with zipfile.ZipFile(final_zip_name, 'w', zipfile.ZIP_DEFLATED) as zip_final:
        zip_final.write(app_zip_path)
        zip_final.write(update_webapp_path)
        zip_final.write(metadata_path)
    print(f"Successfully created final OmniSD package: {final_zip_name}!")

    # 6. Clean up temporary archives in the root to keep it tidy
    if os.path.exists(app_zip_path):
        os.remove(app_zip_path)
    if os.path.exists(update_webapp_path):
        os.remove(update_webapp_path)
    # Note: we can keep metadata.json in the workspace root as it is part of the repo configuration
    
    print("\n--- OMNISD PACKAGING COMPLETED SUCCESSFULY ---")

if __name__ == "__main__":
    main()
