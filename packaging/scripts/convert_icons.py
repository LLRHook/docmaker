#!/usr/bin/env python3
"""Convert SVG icon to platform-specific formats.

Usage:
    python convert_icons.py path/to/icon.svg

Creates:
    - icon.ico (Windows, multi-resolution)
    - icon.icns (macOS)
    - icon.png (Linux, 256x256)

On Windows, this script uses Pillow. For best SVG rendering quality,
you can optionally install svglib: pip install svglib reportlab
"""

import argparse
import io
import struct
import subprocess
import sys
from pathlib import Path


def render_svg_to_png(svg_path: Path, size: int) -> bytes:
    """Render SVG to PNG at specified size.

    Tries multiple backends in order of preference.
    """
    # Try svglib first (pure Python, good quality)
    try:
        from svglib.svglib import svg2rlg
        from reportlab.graphics import renderPM

        drawing = svg2rlg(str(svg_path))
        if drawing:
            # Scale to target size
            scale_x = size / drawing.width
            scale_y = size / drawing.height
            scale = min(scale_x, scale_y)
            drawing.width = size
            drawing.height = size
            drawing.scale(scale, scale)

            png_data = renderPM.drawToString(drawing, fmt="PNG")
            return png_data
    except ImportError:
        pass
    except Exception as e:
        print(f"svglib failed: {e}, trying fallback...")

    # Try cairosvg (requires native Cairo library)
    try:
        import cairosvg
        return cairosvg.svg2png(url=str(svg_path), output_width=size, output_height=size)
    except ImportError:
        pass
    except OSError:
        pass  # Cairo library not found

    # Fallback: create a simple colored square as placeholder
    print(f"Warning: No SVG renderer available. Creating placeholder icon.")
    print("For better icons, install: pip install svglib reportlab")

    from PIL import Image, ImageDraw

    img = Image.new("RGBA", (size, size), (79, 70, 229, 255))  # Purple background
    draw = ImageDraw.Draw(img)

    # Draw a simple "D" letter
    margin = size // 4
    draw.rectangle([margin, margin, size - margin, size - margin],
                   fill=(255, 255, 255, 240))

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


def check_pillow():
    """Check if Pillow is available."""
    try:
        from PIL import Image  # noqa: F401
        return True
    except ImportError:
        print("Error: Pillow not installed.")
        print("Install with: pip install pillow")
        sys.exit(1)


def create_ico(svg_path: Path, output_path: Path):
    """Create Windows ICO file with multiple resolutions."""
    from PIL import Image

    # Standard Windows icon sizes
    sizes = [16, 24, 32, 48, 64, 128, 256]
    images = []

    for size in sizes:
        png_data = render_svg_to_png(svg_path, size)
        img = Image.open(io.BytesIO(png_data))
        # Ensure RGBA mode
        if img.mode != "RGBA":
            img = img.convert("RGBA")
        images.append(img)

    # Save as ICO (Pillow handles the multi-size ICO format)
    images[-1].save(
        output_path,
        format="ICO",
        sizes=[(s, s) for s in sizes],
        append_images=images[:-1]
    )
    print(f"Created: {output_path}")


def create_icns(svg_path: Path, output_path: Path):
    """Create macOS ICNS file."""
    import platform

    # macOS icon sizes (iconset naming convention)
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

    # Check if we're on macOS and can use iconutil
    if platform.system() == "Darwin":
        # Create temporary iconset directory
        iconset_dir = output_path.parent / "docmaker.iconset"
        iconset_dir.mkdir(exist_ok=True)

        for name, size in iconset_sizes.items():
            png_data = render_svg_to_png(svg_path, size)
            (iconset_dir / name).write_bytes(png_data)

        # Use iconutil to create ICNS
        try:
            subprocess.run(
                ["iconutil", "-c", "icns", str(iconset_dir), "-o", str(output_path)],
                check=True,
                capture_output=True,
            )
            print(f"Created: {output_path}")
        except subprocess.CalledProcessError as e:
            print(f"Error creating ICNS: {e.stderr.decode()}")
            sys.exit(1)
        finally:
            # Clean up iconset
            import shutil
            shutil.rmtree(iconset_dir, ignore_errors=True)
    else:
        # On non-macOS, create a simple ICNS manually
        print(f"Note: Full ICNS creation requires macOS. Creating simplified ICNS at {output_path}")
        png_data = render_svg_to_png(svg_path, 512)
        create_simple_icns(png_data, output_path)


def create_simple_icns(png_data: bytes, output_path: Path):
    """Create a simple ICNS file with PNG data (cross-platform fallback)."""
    # ICNS format: 'icns' magic + total size + icon entries
    # ic09 = 512x512 PNG

    icon_type = b"ic09"  # 512x512 PNG
    icon_data = png_data
    icon_size = len(icon_data) + 8  # type + size + data

    # Total file: magic(4) + total_size(4) + icon_entry
    total_size = 8 + icon_size

    with open(output_path, "wb") as f:
        f.write(b"icns")  # Magic
        f.write(struct.pack(">I", total_size))  # Total size (big-endian)
        f.write(icon_type)  # Icon type
        f.write(struct.pack(">I", icon_size))  # Icon size (big-endian)
        f.write(icon_data)  # PNG data

    print(f"Created: {output_path}")


def create_png(svg_path: Path, output_path: Path, size: int = 256):
    """Create PNG file for Linux."""
    png_data = render_svg_to_png(svg_path, size)
    output_path.write_bytes(png_data)
    print(f"Created: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Convert SVG icon to platform-specific formats")
    parser.add_argument("svg_path", type=Path, help="Path to source SVG file")
    parser.add_argument("--output-dir", "-o", type=Path, help="Output directory (default: same as SVG)")
    args = parser.parse_args()

    check_pillow()

    svg_path = args.svg_path.resolve()
    if not svg_path.exists():
        print(f"Error: SVG file not found: {svg_path}")
        sys.exit(1)

    output_dir = args.output_dir or svg_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    base_name = svg_path.stem

    # Create all formats
    print(f"Converting {svg_path.name}...")
    create_ico(svg_path, output_dir / f"{base_name}.ico")
    create_icns(svg_path, output_dir / f"{base_name}.icns")
    create_png(svg_path, output_dir / f"{base_name}.png", size=256)

    print("\nIcon conversion complete!")


if __name__ == "__main__":
    main()
