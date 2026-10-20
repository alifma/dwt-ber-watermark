"""
Asymmetric post-quantum ML-DSA-44 (FIPS 204) signature over the per-block SHA-256 certificates.

This layer is separate from BER verification:
- BER (verify.py)       : "is the image still intact, and which blocks changed?"
- ML-DSA (this module)  : "who vouches for this certificate, and is it authentic?"

Instead of signing 256 certificates one by one, ONE root hash is computed (SHA-256 of the
deterministic concatenation of all certificates) and that root hash is signed once per image.

IMPORTANT: `dilithium-py` is a pure-Python implementation for research/education, not for
production. Never commit a private key.
"""
import base64
import hashlib

from dilithium_py.ml_dsa import ML_DSA_44

ALGORITHM = "ML-DSA-44 (FIPS 204 / NIST security level 1)"


def generate_keys():
    """Returns (public_key, private_key) as bytes."""
    return ML_DSA_44.keygen()


def compute_root_hash(certificates: dict) -> bytes:
    """Deterministic SHA-256 over all certificates, ordered numerically by (row, col)."""

    def order(item):
        row_idx, col_idx = item[0].split("_")
        return int(row_idx), int(col_idx)

    joined = "|".join(f"{k}:{v}" for k, v in sorted(certificates.items(), key=order))
    return hashlib.sha256(joined.encode("utf-8")).digest()


def sign_certificates(certificates: dict, private_key: bytes) -> dict:
    """Sign the root hash. Returns a JSON-ready dict."""
    root = compute_root_hash(certificates)
    return {
        "algorithm": ALGORITHM,
        "root_hash_sha256": root.hex(),
        "signature_b64": base64.b64encode(ML_DSA_44.sign(private_key, root)).decode("ascii"),
        "block_count": len(certificates),
    }


def build_record(enrollment_id: int, certificates: dict, info: dict, public_key: bytes) -> dict:
    """What the publisher stores for one image (JSON-ready). Contains the PUBLIC key only."""
    return {
        "enrollment_id": enrollment_id,
        "certificates": certificates,
        "signature": info,
        "public_key_b64": base64.b64encode(public_key).decode("ascii"),
    }


def key_fingerprint(public_key: bytes) -> str:
    """Short SHA-256 fingerprint of a public key, to compare against one obtained from the publisher."""
    return hashlib.sha256(public_key).hexdigest()[:16]


def verify(certificates: dict, info: dict, public_key: bytes) -> dict:
    """Returns {"valid": bool, "reason": str}; the reason tells altered certificates from a bad signature."""
    root = compute_root_hash(certificates)
    if root != bytes.fromhex(info["root_hash_sha256"]):
        return {"valid": False, "reason": "Root hash mismatch: the certificates changed after signing."}
    if not ML_DSA_44.verify(public_key, root, base64.b64decode(info["signature_b64"])):
        return {"valid": False, "reason": "Invalid signature for this public key."}
    return {"valid": True, "reason": "Valid signature: the certificates are authentic and intact."}
