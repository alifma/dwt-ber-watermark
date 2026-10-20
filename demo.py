"""
End-to-end demo: embed the watermark, simulate compression and manipulation, verify,
then save the assets (images, BER maps, summary) to the outputs/ folder.

    python demo.py                    # uses the synthetic image
    python demo.py --input photo.png  # uses your own image (PNG/JPEG, colour or grayscale)
"""
import argparse
import base64
import json
import os

import cv2

from wm import embed, imaging as im, robust_id, signing, verify
from wm.config import BER_THRESHOLD

ENROLLMENT_ID = 123456789  # example 32-bit identifier


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", help="input image; the synthetic image is used when omitted")
    ap.add_argument("--out", default="outputs")
    ap.add_argument("--id", type=int, default=ENROLLMENT_ID)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    bgr = im.read_image(args.input)[0] if args.input else im.sample_image(512)
    Y = im.luminance(bgr)
    Y_wm, certificates = embed.embed_luminance(Y, enrollment_id=args.id)
    wm = im.replace_luminance(bgr, Y_wm)
    psnr = float(cv2.PSNR(Y, Y_wm))

    # Keys are generated fresh on every run and are NOT saved to disk.
    pub, priv = signing.generate_keys()
    info = signing.sign_certificates(certificates, priv)

    h, w = Y.shape[0] // 32, Y.shape[1] // 32
    scenarios = {
        "01_intact": wm,
        "02_jpeg_q90": im.jpeg(wm, 90),
        "03_jpeg_q80": im.jpeg(wm, 80),
        "04_jpeg_q70": im.jpeg(wm, 70),
        "05_local_edit": im.local_edit(wm, h // 3, w // 3),
        "06_splicing": im.splice(wm, (1, 1), (h - 2, w - 2)),
        "07_local_edit_then_jpeg_q90": im.jpeg(im.local_edit(wm, h // 3, w // 3), 90),
    }

    cv2.imwrite(f"{args.out}/00_original.png", bgr)
    cv2.imwrite(f"{args.out}/00_watermarked.png", wm)
    ber_maps, results = {}, {}
    for name, img in scenarios.items():
        cv2.imwrite(f"{args.out}/{name}.png", img)
        r = verify.verify_luminance(im.luminance(img))
        enr, conf = robust_id.extract_id(im.luminance(img))
        cv2.imwrite(f"{args.out}/{name}_map.png", im.overlay(img, r["valid_map"]))
        ber_maps[name] = r["ber_map"]
        results[name] = {
            "percent_valid_blocks": round(r["percent_valid"], 1),
            "invalid_blocks": int((~r["valid_map"]).sum()),
            "mean_ber": round(float(r["ber_map"].mean()), 3),
            "id_read": enr,
            "id_confidence": round(conf, 2),
        }

    # Signature: the original certificates pass; altered certificates are rejected.
    forged = dict(certificates)
    forged["0_0"] = "0" * 64
    results["signature"] = {
        "original_certificates": signing.verify(certificates, info, pub)["valid"],
        "altered_certificates": signing.verify(forged, info, pub)["valid"],
        "signature_bytes": len(base64.b64decode(info["signature_b64"])),
        "public_key_bytes": len(pub),
    }
    summary = {"psnr_db": round(psnr, 2), "ber_threshold": BER_THRESHOLD, "enrollment_id": args.id, "results": results}
    with open(f"{args.out}/results.json", "w") as f:
        json.dump(summary, f, indent=2)
    plot_ber_maps(ber_maps, f"{args.out}/ber_maps_all_scenarios.png")
    # The publisher's record for this image (no private key). Used by verify_image.py.
    with open(f"{args.out}/record.json", "w") as f:
        json.dump(signing.build_record(args.id, certificates, info, pub), f)

    print(f"PSNR (Y) original vs watermarked: {psnr:.2f} dB | block BER threshold = {BER_THRESHOLD}")
    print(f"{'scenario':32s} {'valid%':>7s} {'invalid':>8s} {'mean BER':>9s}  ID")
    for name in scenarios:
        d = results[name]
        print(f"{name:32s} {d['percent_valid_blocks']:7.1f} {d['invalid_blocks']:8d} {d['mean_ber']:9.3f}  {d['id_read']}")
    t = results["signature"]
    print(f"ML-DSA-44 signature: original={t['original_certificates']}, altered certificates={t['altered_certificates']}")
    print(f"Assets saved to {args.out}/")
    print(f"Try the full check: python verify_image.py {args.out}/02_jpeg_q90.png {args.out}/record.json")


def plot_ber_maps(ber_maps: dict, path: str):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    n = len(ber_maps)
    cols = 4
    rows = (n + cols - 1) // cols
    fig, axes = plt.subplots(rows, cols, figsize=(4 * cols, 3.6 * rows), squeeze=False)
    for ax in axes.ravel():
        ax.axis("off")
    for ax, (name, ber_map) in zip(axes.ravel(), ber_maps.items()):
        im_ = ax.imshow(ber_map, vmin=0, vmax=0.55, cmap="viridis")
        ax.contour(ber_map > BER_THRESHOLD, levels=[0.5], colors="red", linewidths=1)
        ax.set_title(name, fontsize=9)
    fig.colorbar(im_, ax=axes, shrink=0.6, label=f"BER per block (red line: > {BER_THRESHOLD})")
    fig.savefig(path, dpi=130, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    main()
