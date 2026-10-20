"""
ROBUST (second) watermark layer: a short identifier (`enrollment_id`) in the LL sub-band.

Goal: after an image passes through a channel that strips metadata and recompresses it (e.g.
WhatsApp), the verifier can still find which enrolment the image came from, then fetch the original
certificate and signature from the server. The semi-fragile layer (HL, embed.py/verify.py) is what
localises manipulation; this layer only carries the identifier.

Design:
- 48-bit payload = 32-bit enrollment_id + 16-bit CRC-16/CCITT-FALSE.
- The LL of each 32x32 block is 16x16 = 256 coefficients. The first 240 (5 copies x 48 bits) are
  used: coefficient i carries payload bit (i % 48).
- QIM embedding with step Q_ID_LL: bit 0 and bit 1 occupy two lattices offset by Q_ID_LL/2.
  ID_DITHER shifts both lattices so their points do not land exactly on a fingerprint
  quantisation boundary (Q_LL_HASH).
- Extraction: every coefficient casts a soft "vote", summed over ALL blocks, then decided per bit.
  A passing CRC means the ID was found; a failing CRC means the image does not carry this watermark.
- Order when embedding: LL is modified FIRST, the fingerprint is computed from the modified LL,
  and only then embedded into HL. That keeps verify.py consistent.

Limitation: resize/rescale shifts the block grid, so extraction fails.
"""
import numpy as np

from .config import BLOCK_SIZE, ID_DITHER, Q_ID_LL, WAVELET
from .dwt import decompose

ID_BITS = 32
CRC_BITS = 16
PAYLOAD_BITS = ID_BITS + CRC_BITS
LL_COEF = (BLOCK_SIZE // 2) ** 2
N_USED = (LL_COEF // PAYLOAD_BITS) * PAYLOAD_BITS
_BIT_INDEX = np.arange(N_USED) % PAYLOAD_BITS


def crc16(data: bytes) -> int:
    """CRC-16/CCITT-FALSE (poly 0x1021, init 0xFFFF)."""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc


def make_payload(enrollment_id: int) -> np.ndarray:
    """enrollment_id (0 .. 2^32-1) -> 48 bits (ID then CRC)."""
    if not 0 <= enrollment_id < 2**ID_BITS:
        raise ValueError("enrollment_id must fit in 32 bits (0 .. 4294967295)")
    value = (enrollment_id << CRC_BITS) | crc16(enrollment_id.to_bytes(4, "big"))
    return np.array([(value >> (PAYLOAD_BITS - 1 - i)) & 1 for i in range(PAYLOAD_BITS)], dtype=np.uint8)


def read_payload(bits: np.ndarray):
    """48 bits -> enrollment_id if the CRC passes, otherwise None."""
    value = 0
    for b in bits:
        value = (value << 1) | int(b)
    enrollment_id, crc = value >> CRC_BITS, value & 0xFFFF
    return enrollment_id if crc16(enrollment_id.to_bytes(4, "big")) == crc else None


def embed_ll(LL: np.ndarray, payload: np.ndarray) -> np.ndarray:
    """Embed the payload into LL (QIM). Returns the new LL; the input is not modified."""
    flat = LL.flatten().copy()
    bit = payload[_BIT_INDEX].astype(np.float64)
    offset = ID_DITHER + bit * (Q_ID_LL / 2.0)
    flat[:N_USED] = np.round((flat[:N_USED] - offset) / Q_ID_LL) * Q_ID_LL + offset
    return flat.reshape(LL.shape)


def _soft_votes(LL: np.ndarray) -> np.ndarray:
    """Soft votes from one block per payload bit (length 48). Positive = leans towards 0."""
    values = LL.flatten()[:N_USED]
    d = []
    for b in (0, 1):
        offset = ID_DITHER + b * (Q_ID_LL / 2.0)
        d.append(np.abs(((values - offset + Q_ID_LL / 2.0) % Q_ID_LL) - Q_ID_LL / 2.0))
    return np.bincount(_BIT_INDEX, weights=d[1] - d[0], minlength=PAYLOAD_BITS)


def extract_id(Y: np.ndarray):
    """
    Y = luminance channel (uint8, 2D). Returns (enrollment_id or None, confidence).
    confidence is 0..1; close to 0 means there is no watermark.
    """
    h = (Y.shape[0] // BLOCK_SIZE) * BLOCK_SIZE
    w = (Y.shape[1] // BLOCK_SIZE) * BLOCK_SIZE
    if h == 0 or w == 0:
        return None, 0.0
    total = np.zeros(PAYLOAD_BITS)
    n_blocks = 0
    for by in range(0, h, BLOCK_SIZE):
        for bx in range(0, w, BLOCK_SIZE):
            LL, _, _, _ = decompose(Y[by : by + BLOCK_SIZE, bx : bx + BLOCK_SIZE].copy(), WAVELET)
            total += _soft_votes(LL)
            n_blocks += 1
    per_coef = total / (n_blocks * (N_USED // PAYLOAD_BITS))
    confidence = float(np.mean(np.abs(per_coef)) / (Q_ID_LL / 4.0))
    return read_payload((per_coef < 0).astype(np.uint8)), confidence
