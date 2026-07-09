"""
Détourage de logo : retire le fond blanc d'un PDF ou d'une image et produit un PNG transparent.

Usage:
    python scripts/remove_logo_bg.py <input.pdf|input.png|input.jpg> [output.png] [--dpi 300] [--white 235] [--edge 180]

Defaults:
    output     = <input_basename>-transparent.png à côté du source
    dpi        = 300 (rastérisation PDF — 400+ explose la RAM sur 8 GB)
    white      = 235 (luminance ≥ ce seuil → alpha 0)
    edge       = 180 (luminance ≤ ce seuil → alpha 255 ; entre les deux → gradué)
"""
import argparse
import os
import sys

import fitz  # PyMuPDF
import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None


def safeprint(*parts):
    msg = " ".join(str(p) for p in parts)
    print(msg.encode("ascii", "replace").decode("ascii"))


def rasterize_pdf(path, dpi):
    doc = fitz.open(path)
    page = doc[0]
    zoom = dpi / 72
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
    tmp_png = os.path.splitext(path)[0] + "_raster.png"
    pix.save(tmp_png)
    doc.close()
    return tmp_png


def remove_white(img, white_threshold, edge_threshold):
    img = img.convert("RGBA")
    arr = np.array(img)
    rgb = arr[..., :3].astype(np.int16)
    lum = rgb.mean(axis=2)

    alpha = np.where(
        lum >= white_threshold, 0,
        np.where(
            lum <= edge_threshold,
            255,
            ((white_threshold - lum) / (white_threshold - edge_threshold) * 255).astype(np.int16),
        ),
    ).astype(np.uint8)

    arr[..., 3] = alpha
    out = Image.fromarray(arr, "RGBA")
    bbox = out.getbbox()
    if bbox:
        out = out.crop(bbox)
    return out


def main():
    ap = argparse.ArgumentParser(description="Detoure un logo : fond blanc -> transparent.")
    ap.add_argument("input", help="Chemin du PDF, PNG ou JPG source")
    ap.add_argument("output", nargs="?", help="Chemin du PNG transparent (defaut : <input>-transparent.png)")
    ap.add_argument("--dpi", type=int, default=300, help="DPI de rasterisation PDF (defaut 300)")
    ap.add_argument("--white", type=int, default=235, help="Seuil luminance fond blanc (defaut 235)")
    ap.add_argument("--edge", type=int, default=180, help="Seuil luminance bord opaque (defaut 180)")
    args = ap.parse_args()

    src = args.input
    if not os.path.exists(src):
        safeprint(f"Introuvable : {src}")
        sys.exit(1)

    safeprint("Source :", src)

    ext = os.path.splitext(src)[1].lower()
    tmp_raster = None
    try:
        if ext == ".pdf":
            tmp_raster = rasterize_pdf(src, args.dpi)
            img = Image.open(tmp_raster)
        else:
            img = Image.open(src)

        result = remove_white(img, args.white, args.edge)

        out = args.output
        if not out:
            base = os.path.splitext(src)[0]
            out = base + "-transparent.png"
        result.save(out, "PNG", optimize=True)
        safeprint(f"OK : {out}  ({result.size[0]}x{result.size[1]} px)")
    finally:
        if tmp_raster and os.path.exists(tmp_raster):
            os.remove(tmp_raster)


if __name__ == "__main__":
    main()
