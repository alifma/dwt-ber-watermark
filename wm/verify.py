"""
Block-wise verification: per-block BER against the fingerprint that should be there.

Verification is blind/self-referential: the fingerprint is recomputed from the LL of the received
image and compared with the bits embedded in HL. The original image is NOT needed.
"""
import numpy as np

from .config import BER_THRESHOLD, BLOCK_SIZE, N_BITS, Q_EMBED, Q_LL_HASH, WAVELET
from .dwt import decompose, grid_positions
from .fingerprint import ber, fingerprint_from_ll


def verify_block(block, row_idx, col_idx) -> float:
    """BER (0.0 - 1.0) of one block against the fingerprint that should be there."""
    LL, _, HL, _ = decompose(block, WAVELET)
    extracted = np.array(
        [round(HL[r, c] / Q_EMBED) % 2 for (r, c) in grid_positions(HL.shape, N_BITS)], dtype=np.uint8
    )
    return ber(extracted, fingerprint_from_ll(LL, Q_LL_HASH, row_idx, col_idx))


def verify_luminance(Y: np.ndarray) -> dict:
    """
    Verify every block of the Y channel.
    Returns {"ber_map", "valid_map", "percent_valid"}.
    """
    h = (Y.shape[0] // BLOCK_SIZE) * BLOCK_SIZE
    w = (Y.shape[1] // BLOCK_SIZE) * BLOCK_SIZE
    ber_map = np.zeros((h // BLOCK_SIZE, w // BLOCK_SIZE))
    for row_idx, by in enumerate(range(0, h, BLOCK_SIZE)):
        for col_idx, bx in enumerate(range(0, w, BLOCK_SIZE)):
            ber_map[row_idx, col_idx] = verify_block(
                Y[by : by + BLOCK_SIZE, bx : bx + BLOCK_SIZE].copy(), row_idx, col_idx
            )
    valid = ber_map <= BER_THRESHOLD
    return {"ber_map": ber_map, "valid_map": valid, "percent_valid": float(valid.mean() * 100)}
