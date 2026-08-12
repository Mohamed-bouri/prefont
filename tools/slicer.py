#!/usr/bin/env python3
"""
IMG-SLICER - Interactive Image Grid Slicer
An interactive tool to slice all images in a directory into grid parts.
By Mohamed BOURI
"""

import sys
import time
from pathlib import Path

# ── Check for Pillow library ────────────────────────────────────────
try:
    from PIL import Image
    PIL_OK = True
except ImportError:
    PIL_OK = False

# ── Banner ──────────────────────────────────────────────────────────
BANNER = r"""
   ___ __  __  ___     ___ _    ___ ___ ___ ___ 
  |_ _|  \/  |/ __|___/ __| |  |_ _/ __| __| _ \
   | || |\/| | (_ |___\__ \ |__ | | (__| _||   /
  |___|_|  |_|\___|   |___/____|___\___|___|_|_\                                
                                By Mohamed BOURI
"""

def _info(text: str):
    print(f"[*] {text}")

def _ok(text: str):
    print(f"[+] {text}")

def _err(text: str):
    print(f"[-] {text}", file=sys.stderr)

def _divider(char: str = "-", width: int = 60):
    print(char * width)

# ── Core Logic ──────────────────────────────────────────────────────
VALID_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.bmp', '.webp', '.tiff'}

def slice_image(img_path: Path, output_dir: Path, cols: int, rows: int) -> bool:
    """Slice a single image into the requested grid and save to output directory."""
    try:
        with Image.open(img_path) as img:
            width, height = img.size
            
            # Calculate base dimensions for each tile
            tile_w = width // cols
            tile_h = height // rows
            
            # Extract name and extension
            base_name = img_path.stem
            ext = img_path.suffix

            part_number = 1
            # Process row by row (horizontal slices first)
            for row in range(rows):
                for col in range(cols):
                    # Calculate crop coordinates (left, upper, right, lower)
                    left = col * tile_w
                    upper = row * tile_h
                    
                    # Ensure remaining pixels on edges are included (prevent edge bleeding)
                    right = width if col == cols - 1 else (col + 1) * tile_w
                    lower = height if row == rows - 1 else (row + 1) * tile_h
                    
                    # Crop the image
                    bbox = (left, upper, right, lower)
                    cropped_img = img.crop(bbox)
                    
                    # Format output filename
                    out_filename = f"{base_name}_part{part_number:02d}{ext}"
                    out_path = output_dir / out_filename
                    
                    # Handle transparency issues when saving as JPEG
                    if cropped_img.mode in ('RGBA', 'P') and ext.lower() in ('.jpg', '.jpeg'):
                        cropped_img = cropped_img.convert('RGB')
                        
                    cropped_img.save(out_path)
                    part_number += 1
                    
        return True
    except Exception as e:
        _err(f"Error processing image '{img_path.name}': {e}")
        return False


# ── Main Interactive CLI ────────────────────────────────────────────
def main():
    print(BANNER)
    _divider("=")
    print("  IMG-SLICER - Interactive Image Slicer")
    _divider("=")
    print()

    if not PIL_OK:
        _err("Pillow library is not installed!")
        print("Please run the following command to install it: pip install Pillow")
        sys.exit(1)

    work_dir = Path(__file__).resolve().parent
    output_dir = work_dir / "output"

    # Find images in the script's directory
    images = [f for f in work_dir.iterdir() if f.is_file() and f.suffix.lower() in VALID_EXTENSIONS]
    
    if not images:
        _err(f"No images found in the directory: {work_dir}")
        print(f"Supported formats: {', '.join(VALID_EXTENSIONS)}")
        sys.exit(1)

    _info(f"Found {len(images)} image(s) in the directory.")
    print()

    # User Interaction Loop
    while True:
        try:
            print("Enter the number of required parts:")
            user_input = input(" (e.g., '4 1' for 4 horizontal rows and 1 vertical column): ").strip()
            
            if not user_input:
                continue
                
            parts = user_input.split()
            if len(parts) != 2:
                _err("Please enter two numbers separated by a space (e.g., 4 1)")
                continue
                
            rows, cols = int(parts[0]), int(parts[1])
            
            if cols <= 0 or rows <= 0:
                _err("Numbers must be greater than zero!")
                continue
                
            break
        except ValueError:
            _err("Invalid input! Please enter valid integers only.")
        except KeyboardInterrupt:
            print()
            _err("Operation cancelled by user.")
            sys.exit(130)

    print()
    _divider("-")
    _info("Setting up workspace...")
    
    # Create output directory if it doesn't exist
    if not output_dir.exists():
        output_dir.mkdir()
        _ok("Created output directory: output/")
    else:
        _info("Output directory output/ already exists.")

    _info(f"Slicing layout: {rows} horizontal rows x {cols} vertical columns.")
    print()

    # Start slicing process
    success_count = 0
    total = len(images)
    
    for i, img_path in enumerate(images, 1):
        print(f"[{i}/{total}] Slicing: {img_path.name} ... ", end="")
        sys.stdout.flush()
        
        if slice_image(img_path, output_dir, cols, rows):
            print("Success!")
            success_count += 1
        else:
            print("Failed!")
            
        time.sleep(0.1) # Brief pause for UI visual effect

    print()
    _divider("=")
    if success_count == total:
        _ok(f"Finished successfully! Processed all images ({success_count}/{total}).")
    else:
        _info(f"Finished. Successfully processed ({success_count}/{total}) image(s).")
        
    print(f"Results saved in: {output_dir.absolute()}")
    _divider("=")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
        _err("Script unexpectedly stopped (KeyboardInterrupt).")
        sys.exit(130)