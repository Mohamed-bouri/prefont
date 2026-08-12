#!/usr/init/env python3
"""
upscablur- Advanced Text & Handwriting Upscaler and Edge Softener
An interactive tool to upscale images first (high-quality Lanczos) and apply 
fine Gaussian blur to smooth text and handwriting edges naturally.
"""

import sys
import time
from pathlib import Path

# ── Check for Pillow library ────────────────────────────────────────
try:
    from PIL import Image, ImageFilter
    PIL_OK = True
except ImportError:
    PIL_OK = False

# ── Banner ──────────────────────────────────────────────────────────
BANNER = r"""
                                ___.   .__                
 __ ________  ______ ____ _____ \_ |__ |  |  __ _________ 
|  |  \____ \/  ___// ___\\__  \ | __ \|  | |  |  \_  __ \
|  |  /  |_> >___ \\  \___ / __ \| \_\ \  |_|  |  /|  | \/
|____/|   __/____  >\___  >____  /___  /____/____/ |__|   
      |__|       \/     \/     \/    \/By Mohamed BOURI 
                                                
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

def process_image(img_path: Path, output_dir: Path, scale_factor: float, blur_radius: float) -> bool:
    """Upscale image first using high-quality Lanczos, then apply fine Gaussian blur."""
    try:
        with Image.open(img_path) as img:
            width, height = img.size
            
            # Step 1: Upscale dimensions first (crucial for smooth text edges)
            new_width = int(width * scale_factor)
            new_height = int(height * scale_factor)
            
            resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Step 2: Apply fine Gaussian Blur for natural ink/pen edge softening
            if blur_radius > 0:
                resized_img = resized_img.filter(ImageFilter.GaussianBlur(radius=blur_radius))
            
            # Format output filename
            base_name = img_path.stem
            ext = img_path.suffix
            out_filename = f"{base_name}_smoothed{ext}"
            out_path = output_dir / out_filename
            
            # Handle transparency issues when saving as JPEG
            if resized_img.mode in ('RGBA', 'P') and ext.lower() in ('.jpg', '.jpeg'):
                resized_img = resized_img.convert('RGB')
                
            resized_img.save(out_path, quality=95)
            
        return True
    except Exception as e:
        _err(f"Error processing image '{img_path.name}': {e}")
        return False


# ── Main Interactive CLI ────────────────────────────────____________
def main():
    print(BANNER)
    _divider("=")
    print("  IMG-SMOOTHER - Text & Handwriting Edge Optimizer")
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

    # Step 1: Ask for upscale percentage
    scale_factor = 1.0
    while True:
        try:
            print("Step 1: Enter upscale percentage (Recommended: 300% to 500% for text):")
            user_input = input(" (e.g., '400' for 400%): ").strip().lower()
            user_input = user_input.replace('%', '')
            
            if not user_input:
                continue
                
            val = float(user_input)
            if val <= 0:
                _err("Percentage must be greater than zero!")
                continue
            
            scale_factor = val / 100.0
            break
        except ValueError:
            _err("Invalid input! Please enter a valid number (e.g., 400).")
        except KeyboardInterrupt:
            print()
            _err("Operation cancelled by user.")
            sys.exit(130)

    print()

    # Step 2: Ask for Gaussian blur radius
    blur_radius = 0.0
    while True:
        try:
            print("Step 2: Enter Gaussian blur radius for edge softening:")
            user_input = input(" (Recommended for text/handwriting: '0.5' to '1.5', or '0' for none): ").strip()
            
            if not user_input:
                blur_radius = 0.0
                break
                
            val = float(user_input)
            if val < 0:
                _err("Blur radius cannot be negative!")
                continue
                
            blur_radius = val
            break
        except ValueError:
            _err("Invalid input! Please enter a valid number (e.g., 0.8 or 1.0).")
        except KeyboardInterrupt:
            print()
            _err("Operation cancelled by user.")
            sys.exit(130)

    print()
    _divider("-")
    _info("Setting up workspace...")
    
    # Create output directory beside the script if it doesn't exist
    if not output_dir.exists():
        output_dir.mkdir()
        _ok("Created output directory: output/")
    else:
        _info("Output directory output/ already exists.")

    _info(f"Configuration: Upscale by {scale_factor * 100:.0f}% (Lanczos) | Blur radius: {blur_radius}")
    print()

    # Start processing images
    success_count = 0
    total = len(images)
    
    for i, img_path in enumerate(images, 1):
        print(f"[{i}/{total}] Processing: {img_path.name} ... ", end="")
        sys.stdout.flush()
        
        if process_image(img_path, output_dir, scale_factor, blur_radius):
            print("Success!")
            success_count += 1
        else:
            print("Failed!")
            
        time.sleep(0.1)

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
