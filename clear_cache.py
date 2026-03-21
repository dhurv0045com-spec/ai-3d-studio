import os
import shutil

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(BASE_DIR, 'models')
CACHE_DIR = os.path.join(MODELS_DIR, 'cache')
PRESETS_DIR = os.path.join(MODELS_DIR, 'presets')

def clear_dir(path):
    if not os.path.exists(path):
        print(f"Directory not found: {path}")
        return
    
    count = 0
    for f in os.listdir(path):
        if f.endswith('.glb'):
            file_path = os.path.join(path, f)
            try:
                os.remove(file_path)
                count += 1
            except Exception as e:
                print(f"Error removing {f}: {e}")
    print(f"Cleared {count} .glb files from {path}")

if __name__ == "__main__":
    print("Clearing model cache...")
    clear_dir(CACHE_DIR)
    clear_dir(PRESETS_DIR)
    print("Done.")
