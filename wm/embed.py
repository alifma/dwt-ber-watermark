"""
Block-wise watermark embedding on the luminance (Y) channel.

Per 32x32 block: DWT -> (optional) plant the robust ID in LL -> compute the fingerprint from LL ->
embed the fingerprint into HL (parity QIM, 1 bit per coefficient) -> inverse DWT.

Each block is processed in isolation (explicit copy) and written to a new canvas.
"""
import numpy as np

from .config import BLOCK_SIZE, N_BITS, Q_EMBED, Q_LL_HASH, WAVELET
from .dwt import decompose, grid_positions, reconstruct
from .fingerprint import block_certificate, fingerprint_from_ll


def embed_block(block, row_idx, col_idx, payload_id=None):
    """Embed into ONE block. Returns (watermarked block, the LL used for the certificate)."""
    LL, LH, HL, HH = decompose(block, WAVELET)
    if payload_id is not None:
        from .robust_id import embed_ll

        LL = embed_ll(LL, payload_id)

    bits = fingerprint_from_ll(LL, Q_LL_HASH, row_idx, col_idx)
    HL_new = HL.copy()
    for (r, c), b in zip(grid_positions(HL.shape, N_BITS), bits):
        q = round(HL_new[r, c] / Q_EMBED)
        if (q % 2) != b:
            q += 1
        HL_new[r, c] = q * Q_EMBED

    return reconstruct(LL, LH, HL_new, HH, WAVELET), LL


def embed_luminance(Y: np.ndarray, enrollment_id: int = None):
    """
    Watermark a whole Y channel (uint8, 2D). Edge strips that are not a multiple of BLOCK_SIZE are
    left untouched. Returns (new Y, certificates) where certificates = {"row_col": sha256_hex}.
    """
    payload_id = None
    if enrollment_id is not None:
        from .robust_id import make_payload

        payload_id = make_payload(enrollment_id)

    h = (Y.shape[0] // BLOCK_SIZE) * BLOCK_SIZE
    w = (Y.shape[1] // BLOCK_SIZE) * BLOCK_SIZE
    out = Y.copy()
    certificates = {}
    for row_idx, by in enumerate(range(0, h, BLOCK_SIZE)):
        for col_idx, bx in enumerate(range(0, w, BLOCK_SIZE)):
            block = Y[by : by + BLOCK_SIZE, bx : bx + BLOCK_SIZE].copy()
            block_wm, LL = embed_block(block, row_idx, col_idx, payload_id)
            out[by : by + BLOCK_SIZE, bx : bx + BLOCK_SIZE] = block_wm
            certificates[f"{row_idx}_{col_idx}"] = block_certificate(LL, Q_LL_HASH)
    return out, certificates
