#!/usr/bin/env python3
"""
SLICEBLUR - Grid Slicer + Upscale/Blur Pipeline
A two-stage interactive tool:
  Stage 1 (Slicer)    slices every image in the script's directory into a
                       grid of parts.
  Stage 2 (UpscaBlur)  takes ONLY the parts Stage 1 just produced and, for
                       each one, upscales it first (high-quality Lanczos)
                       and then applies a fine Gaussian blur to smooth
                       text/handwriting edges -- strictly in that order.
By Mohamed BOURI
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

# ── Check for Pillow library ────────────────────────────────────────
try:
    from PIL import Image, ImageFilter
    PIL_OK = True
except ImportError:
    PIL_OK = False

# ── Banners (one per stage, shown when that stage begins) ───────────
SLICER_BANNER = r"""
   ___ __  __  ___     ___ _    ___ ___ ___ ___ 
  |_ _|  \/  |/ __|___/ __| |  |_ _/ __| __| _ \
   | || |\/| | (_ |___\__ \ |__ | | (__| _||   /
  |___|_|  |_|\___|   |___/____|___\___|___|_|_\                                
                                By Mohamed BOURI
"""

UPSCABLUR_BANNER = r"""
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


def _section(title: str):
    print()
    _divider("=")
    print(f"  {title}")
    _divider("=")
    print()


# ── Shared ────────────────────────────────────────────────────────────
VALID_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.bmp', '.webp', '.tiff'}


def find_images(folder: Path) -> list[Path]:
    """Image files directly inside `folder` (non-recursive), sorted for a
    stable, predictable processing order. Non-recursive on purpose: a
    stage's own output subdirectory sits *beside* its input, not inside
    it, so it's never picked back up as input by accident."""
    return sorted(f for f in folder.iterdir() if f.is_file() and f.suffix.lower() in VALID_EXTENSIONS)


# ── Stage 1: Slicer ─────────────────────────────────────────────────

def slice_image(img_path: Path, output_dir: Path, cols: int, rows: int) -> bool:
    """Slice a single image into the requested grid and save to output directory."""
    try:
        with Image.open(img_path) as img:
            width, height = img.size

            # Calculate base dimensions for each tile
            tile_w = width // cols
            tile_h = height // rows

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

                    bbox = (left, upper, right, lower)
                    cropped_img = img.crop(bbox)

                    out_filename = f"{base_name}_part{part_number:02d}{ext}"
                    out_path = output_dir / out_filename

                    # Handle transparency issues when saving as JPEG
                    if cropped_img.mode in ('RGBA', 'P') and ext.lower() in ('.jpg', '.jpeg'):
                        cropped_img = cropped_img.convert('RGB')

                    cropped_img.save(out_path)
                    part_number += 1

        return True
    except Exception as e:
        _err(f"Error slicing image '{img_path.name}': {e}")
        return False


def run_slice_stage(source_dir: Path, output_dir: Path, rows: int, cols: int) -> int:
    """Slice every image found directly in source_dir into output_dir.
    Returns how many source images were successfully sliced."""
    images = find_images(source_dir)
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

        time.sleep(0.1)

    return success_count


# ── Stage 2: UpscaBlur ───────────────────────────────────────────────

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


def run_upscablur_stage(source_dir: Path, output_dir: Path, scale_factor: float, blur_radius: float) -> int:
    """Upscale-then-blur every image found directly in source_dir into
    output_dir. Returns how many were successfully processed."""
    images = find_images(source_dir)
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

    return success_count


# ── Interactive prompts ──────────────────────────────────────────────

def ask_grid() -> tuple[int, int]:
    """Ask for the slicing grid. Returns (rows, cols)."""
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

            return rows, cols
        except ValueError:
            _err("Invalid input! Please enter valid integers only.")
        except (KeyboardInterrupt, EOFError):
            print()
            _err("Operation cancelled by user.")
            sys.exit(130)


def ask_scale() -> float:
    """Ask for the upscale percentage. Returns a scale factor (e.g. 4.0 for 400%)."""
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

            return val / 100.0
        except ValueError:
            _err("Invalid input! Please enter a valid number (e.g., 400).")
        except (KeyboardInterrupt, EOFError):
            print()
            _err("Operation cancelled by user.")
            sys.exit(130)


def ask_blur() -> float:
    """Ask for the Gaussian blur radius. Returns 0.0 if left blank."""
    while True:
        try:
            print("Step 2: Enter Gaussian blur radius for edge softening:")
            user_input = input(" (Recommended for text/handwriting: '0.5' to '1.5', or '0' for none): ").strip()

            if not user_input:
                return 0.0

            val = float(user_input)
            if val < 0:
                _err("Blur radius cannot be negative!")
                continue

            return val
        except ValueError:
            _err("Invalid input! Please enter a valid number (e.g., 0.8 or 1.0).")
        except (KeyboardInterrupt, EOFError):
            print()
            _err("Operation cancelled by user.")
            sys.exit(130)


# ── Order selection ───────────────────────────────────────────────────

def ask_order() -> str:
    """Ask the user which stage should run first this session.
    Returns 'blur_first' or 'slice_first'. Stage 1 (UpscaBlur) and
    Stage 2 (Slicer) are fixed names for the two tools -- this choice
    only controls which one runs first and which one runs second."""
    while True:
        try:
            print("Which would you like to run first?")
            print("  [1] Stage 1 - UpscaBlur (upscale then blur) first, then Stage 2 - Slicer")
            print("  [2] Stage 2 - Slicer first, then Stage 1 - UpscaBlur (upscale then blur)")
            choice = input(" Choice (1/2): ").strip()
            if choice == "1":
                return "blur_first"
            if choice == "2":
                return "slice_first"
            _err("Please enter 1 or 2.")
        except (KeyboardInterrupt, EOFError):
            print()
            _err("Operation cancelled by user.")
            sys.exit(130)


# ── Stage runners (each owns its own banner, prompts, and I/O) ────────

def stage_upscablur(source_dir: Path, output_dir: Path, source_label: str, position: int) -> int:
    """Runs the UpscaBlur stage end-to-end against every image directly
    inside source_dir, saving results to output_dir. Returns how many
    images were processed successfully (0 if the source had no images)."""
    print(UPSCABLUR_BANNER)
    _section(f"STAGE 1 - UPSCABLUR: upscale then blur  [running {position}/2 this session]")

    images = find_images(source_dir)
    if not images:
        _err(f"No images found in: {source_dir}")
        return 0

    _info(f"Found {len(images)} {source_label} to process.")
    print()

    scale_factor = ask_scale()
    print()
    blur_radius = ask_blur()

    print()
    _divider("-")
    _info("Setting up workspace...")

    if not output_dir.exists():
        output_dir.mkdir()
        _ok(f"Created directory: {output_dir.name}/")
    else:
        _info(f"Directory {output_dir.name}/ already exists (new results will be added to it).")

    _info(f"Configuration: Upscale by {scale_factor * 100:.0f}% (Lanczos) | Blur radius: {blur_radius}")
    print()

    success = run_upscablur_stage(source_dir, output_dir, scale_factor, blur_radius)

    print()
    _divider("=")
    if success == len(images):
        _ok(f"Stage 1 finished successfully! Processed all images ({success}/{len(images)}).")
    else:
        _info(f"Stage 1 finished. Successfully processed ({success}/{len(images)}) image(s).")
    print(f"Results saved in: {output_dir.absolute()}")
    _divider("=")
    return success


def stage_slicer(source_dir: Path, output_dir: Path, source_label: str, position: int) -> int:
    """Runs the Slicer stage end-to-end against every image directly
    inside source_dir, saving parts to output_dir. Returns how many
    source images were sliced successfully (0 if the source had no images)."""
    print(SLICER_BANNER)
    _section(f"STAGE 2 - IMG-SLICER: slicing images  [running {position}/2 this session]")

    images = find_images(source_dir)
    if not images:
        _err(f"No images found in: {source_dir}")
        return 0

    _info(f"Found {len(images)} {source_label} to slice.")
    print()

    rows, cols = ask_grid()

    print()
    _divider("-")
    _info("Setting up workspace...")

    if not output_dir.exists():
        output_dir.mkdir()
        _ok(f"Created directory: {output_dir.name}/")
    else:
        _info(f"Directory {output_dir.name}/ already exists (new parts will be added to it).")

    _info(f"Slicing layout: {rows} horizontal rows x {cols} vertical columns.")
    print()

    success = run_slice_stage(source_dir, output_dir, rows, cols)

    print()
    _divider("=")
    if success == len(images):
        _ok(f"Stage 2 finished successfully! Sliced all images ({success}/{len(images)}).")
    else:
        _info(f"Stage 2 finished. Successfully sliced ({success}/{len(images)}) image(s).")
    print(f"Sliced parts saved in: {output_dir.absolute()}")
    _divider("=")
    return success


# ── Main Interactive CLI ─────────────────────────────────────────────

def main():
    _divider("=")
    print("  SLICEBLUR - Slice + Upscale/Blur Pipeline")
    _divider("=")
    print()

    if not PIL_OK:
        _err("Pillow library is not installed!")
        print("Please run the following command to install it: pip install Pillow")
        sys.exit(1)

    work_dir = Path(__file__).resolve().parent

    source_images = find_images(work_dir)
    if not source_images:
        _err(f"No images found in the directory: {work_dir}")
        print(f"Supported formats: {', '.join(sorted(VALID_EXTENSIONS))}")
        sys.exit(1)

    _info(f"Found {len(source_images)} image(s) in the script's directory.")
    print()

    order = ask_order()
    print()

    final_dir = work_dir / "output"   # whichever stage runs 2nd always writes the final result here

    if order == "blur_first":
        smoothed_dir = work_dir / "smoothed"
        first_success = stage_upscablur(work_dir, smoothed_dir, "image(s) in the script's directory", position=1)
        if first_success == 0:
            _err("Stage 1 produced no results, so there is nothing for Stage 2 to slice. Stopping.")
            sys.exit(1)
        second_success = stage_slicer(smoothed_dir, final_dir, "smoothed image(s) from Stage 1", position=2)
        first_dir, first_label = smoothed_dir, "Stage 1 output (upscaled + blurred)"
        second_label = "Stage 2 output (final, sliced)"
    else:
        sliced_dir = work_dir / "sliced"
        first_success = stage_slicer(work_dir, sliced_dir, "image(s) in the script's directory", position=1)
        if first_success == 0:
            _err("Stage 2 produced no parts, so there is nothing for Stage 1 to process. Stopping.")
            sys.exit(1)
        second_success = stage_upscablur(sliced_dir, final_dir, "sliced part(s) from Stage 2", position=2)
        first_dir, first_label = sliced_dir, "Stage 2 output (sliced parts)"
        second_label = "Stage 1 output (final, upscaled + blurred)"

    if second_success == 0:
        _err("The second stage produced no results. Check the errors above.")
        sys.exit(1)

    # ================= Pipeline summary ================= #
    print()
    _divider("=")
    _ok("Pipeline complete.")
    label_width = max(len(first_label), len(second_label)) + 1
    print(f"  {(first_label + ':').ljust(label_width)} {first_dir.absolute()}")
    print(f"  {(second_label + ':').ljust(label_width)} {final_dir.absolute()}")
    _divider("=")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
        _err("Script unexpectedly stopped (KeyboardInterrupt).")
        sys.exit(130)
    except EOFError:
        print()
        _err("Script unexpectedly stopped (no more input available).")
        sys.exit(130)
