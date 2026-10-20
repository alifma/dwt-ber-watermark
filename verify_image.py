"""
Full check of a received image against the publisher's record (written by demo.py as record.json):

    1. read the robust ID from the image and compare it with the record
    2. verify the ML-DSA-44 signature over the record's certificates
    3. per-block BER on the image itself (the original image is not needed)

    python verify_image.py received.png outputs/record.json
"""
import argparse
import base64
import json
import sys

from wm import imaging as im, robust_id, signing, verify


def check(image_path: str, record_path: str) -> dict:
    with open(record_path) as f:
        rec = json.load(f)
    _, Y = im.read_image(image_path)

    found_id, confidence = robust_id.extract_id(Y)
    pub = base64.b64decode(rec["public_key_b64"])
    sig = signing.verify(rec["certificates"], rec["signature"], pub)
    r = verify.verify_luminance(Y)
    return {
        "id_found": found_id,
        "id_matches": found_id == rec["enrollment_id"],
        "id_confidence": round(confidence, 2),
        "signature_valid": sig["valid"],
        "signature_reason": sig["reason"],
        "key_fingerprint": signing.key_fingerprint(pub),
        "percent_valid": r["percent_valid"],
        "invalid_blocks": [(int(i), int(j)) for i, j in zip(*(~r["valid_map"]).nonzero())],
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("image")
    ap.add_argument("record")
    args = ap.parse_args()
    res = check(args.image, args.record)

    print(f"1. ID in image      : {res['id_found']}  (matches record: {res['id_matches']}, confidence {res['id_confidence']})")
    print(f"2. Signature        : {'VALID' if res['signature_valid'] else 'INVALID'}  - {res['signature_reason']}")
    print(f"   public key       : fingerprint {res['key_fingerprint']}")
    print(f"3. Blocks valid     : {res['percent_valid']:.1f}%  | suspicious blocks (row, col): {res['invalid_blocks'][:10]}"
          + (" ..." if len(res["invalid_blocks"]) > 10 else ""))
    print()
    print("Note: the signature vouches for the RECORD, not for the pixels. Pixels are judged only by step 3.")
    print("Trust the public key only if its fingerprint matches one you got from the publisher.")
    ok = res["id_matches"] and res["signature_valid"] and not res["invalid_blocks"]
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
