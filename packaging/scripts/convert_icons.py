#!/usr/bin/env python3
"""Convert SVG icon to platform-specific formats.

Usage:
    python convert_icons.py path/to/icon.svg

Creates:
    - icon.ico (Windows - multi-resolution: 16, 24, 32, 48, 64, 128, 256)
    - icon.icns (macOS - 512x512 PNG wrapped in ICNS container)
    - icon.png (Linux - 256x256)

This script uses Playwright to render SVG with full CSS/gradient support.
Install with: pip install playwright && playwright install chromium
"""

import argparse
import io
import struct
import subprocess
import sys
from pathlib import Path


def check_playwright():
    """Check if Playwright is available and Chromium is installed."""
    try:
        from playwright.sync_api import sync_playwright
        # Quick check if browser is installed
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch(headless=True)
                browser.close()
                return True
            except Exception:
                print("Chromium not installed. Run: playwright install chromium")
                return False
    except ImportError:
        print("Playwright not installed. Run: pip install playwright")
        return False


def render_svg_with_playwright(svg_path: Path, size: int) -> bytes:
    """Render SVG to PNG using Playwright (headless Chromium)."""
    from playwright.sync_api import sync_playwright

    svg_content = svg_path.read_text(encoding="utf-8")

    # Create HTML that renders the SVG at exact size
    html = f"""<!DOCTYPE html>
<html>
<head>
    <style>
        * {{ margin: 0; padding: 0; }}
        body {{
            width: {size}px;
            height: {size}px;
            overflow: hidden;
            background: transparent;
        }}
        svg {{
            width: {size}px;
            height: {size}px;
        }}
    </style>
</head>
<body>{svg_content}</body>
</html>"""

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": size, "height": size})
        page.set_content(html)

        # Screenshot the page
        png_bytes = page.screenshot(
            type="png",
            omit_background=True,  # Transparent background
            clip={"x": 0, "y": 0, "width": size, "height": size}
        )

        browser.close()
        return png_bytes


def create_ico(svg_path: Path, output_path: Path):
    """Create Windows ICO file with multiple resolutions.

    ICO spec: https://en.wikipedia.org/wiki/ICO_(file_format)
    Sizes: 16, 24, 32, 48, 64, 128, 256 pixels
    """
    from PIL import Image

    sizes = [16, 24, 32, 48, 64, 128, 256]
    images = []

    print(f"  Rendering {len(sizes)} sizes for ICO...")
    for size in sizes:
        png_data = render_svg_with_playwright(svg_path, size)
        img = Image.open(io.BytesIO(png_data))
        if img.mode != "RGBA":
            img = img.convert("RGBA")
        images.append(img)

    # Save as ICO - Pillow handles multi-resolution ICO format
    images[-1].save(
        output_path,
        format="ICO",
        sizes=[(s, s) for s in sizes],
        append_images=images[:-1]
    )
    print(f"  Created: {output_path}")


def create_icns(svg_path: Path, output_path: Path):
    """Create macOS ICNS file.

    On macOS: Uses iconutil for proper ICNS with all sizes
    On other OS: Creates simplified ICNS with 512x512 PNG (ic09 format)

    ICNS spec: https://en.wikipedia.org/wiki/Apple_Icon_Image_format
    """
    import platform

    if platform.system() == "Darwin":
        # macOS: Use iconutil for full ICNS support
        iconset_sizes = {
            "icon_16x16.png": 16,
            "icon_16x16@2x.png": 32,
            "icon_32x32.png": 32,
            "icon_32x32@2x.png": 64,
            "icon_128x128.png": 128,
            "icon_128x128@2x.png": 256,
            "icon_256x256.png": 256,
            "icon_256x256@2x.png": 512,
            "icon_512x512.png": 512,
            "icon_512x512@2x.png": 1024,
        }

        iconset_dir = output_path.parent / "docmaker.iconset"
        iconset_dir.mkdir(exist_ok=True)

        print(f"  Rendering {len(iconset_sizes)} sizes for ICNS...")
        for name, size in iconset_sizes.items():
            png_data = render_svg_with_playwright(svg_path, size)
            (iconset_dir / name).write_bytes(png_data)

        try:
            subprocess.run(
                ["iconutil", "-c", "icns", str(iconset_dir), "-o", str(output_path)],
                check=True,
                capture_output=True,
            )
            print(f"  Created: {output_path}")
        except subprocess.CalledProcessError as e:
            print(f"  Error creating ICNS: {e.stderr.decode()}")
            sys.exit(1)
        finally:
            import shutil
            shutil.rmtree(iconset_dir, ignore_errors=True)
    else:
        # Non-macOS: Create simplified ICNS with 512x512 PNG
        print("  Note: Full ICNS requires macOS. Creating simplified ICNS...")
        png_data = render_svg_with_playwright(svg_path, 512)

        # ICNS format: magic(4) + size(4) + [type(4) + size(4) + data]...
        icon_type = b"ic09"  # 512x512 PNG
        icon_entry_size = 8 + len(png_data)  # type + size + data
        total_size = 8 + icon_entry_size  # header + entry

        with open(output_path, "wb") as f:
            f.write(b"icns")  # Magic number
            f.write(struct.pack(">I", total_size))  # Total file size (big-endian)
            f.write(icon_type)  # Icon type
            f.write(struct.pack(">I", icon_entry_size))  # Entry size
            f.write(png_data)  # PNG data

        print(f"  Created: {output_path}")


def create_png(svg_path: Path, output_path: Path, size: int = 256):
    """Create PNG file for Linux.

    Standard size: 256x256 for hicolor theme
    """
    print(f"  Rendering {size}x{size} PNG...")
    png_data = render_svg_with_playwright(svg_path, size)
    output_path.write_bytes(png_data)
    print(f"  Created: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Convert SVG icon to platform-specific formats (ICO, ICNS, PNG)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Output specifications:
  ICO (Windows):  Multi-resolution (16, 24, 32, 48, 64, 128, 256px)
  ICNS (macOS):   512x512 PNG in ICNS container (full iconset on macOS)
  PNG (Linux):    256x256 for hicolor icon theme

Requirements:
  pip install playwright pillow
  playwright install chromium
"""
    )
    parser.add_argument("svg_path", type=Path, help="Path to source SVG file")
    parser.add_argument("--output-dir", "-o", type=Path,
                        help="Output directory (default: same as SVG)")
    parser.add_argument("--ico-only", action="store_true", help="Only create ICO")
    parser.add_argument("--icns-only", action="store_true", help="Only create ICNS")
    parser.add_argument("--png-only", action="store_true", help="Only create PNG")
    args = parser.parse_args()

    # Check dependencies
    try:
        from PIL import Image  # noqa: F401
    except ImportError:
        print("Error: Pillow not installed. Run: pip install pillow")
        sys.exit(1)

    if not check_playwright():
        sys.exit(1)

    svg_path = args.svg_path.resolve()
    if not svg_path.exists():
        print(f"Error: SVG file not found: {svg_path}")
        sys.exit(1)

    output_dir = args.output_dir or svg_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    base_name = svg_path.stem
    create_all = not (args.ico_only or args.icns_only or args.png_only)

    print(f"Converting: {svg_path.name}")
    print(f"Output to:  {output_dir}")
    print()

    if create_all or args.ico_only:
        print("Creating Windows ICO...")
        create_ico(svg_path, output_dir / f"{base_name}.ico")
        print()

    if create_all or args.icns_only:
        print("Creating macOS ICNS...")
        create_icns(svg_path, output_dir / f"{base_name}.icns")
        print()

    if create_all or args.png_only:
        print("Creating Linux PNG...")
        create_png(svg_path, output_dir / f"{base_name}.png", size=256)
        print()

    print("Icon conversion complete!")


if __name__ == "__main__":
    main()
