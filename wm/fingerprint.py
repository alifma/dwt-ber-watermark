"""Per-block fingerprint, SHA-256 certificate, and Bit Error Rate (BER)."""
import hashlib

import numpy as np


def position_salt(row_idx: int, col_idx: int, n_bits: int = 256) -> np.ndarray:
    """
    Deterministic bits unique to the block COORDINATE. They bind the fingerprint to its position,
    so a block copied from elsewhere in the same image (splicing) no longer matches its new position.
    """
    seed = hashlib.sha256(f"{row_idx}:{col_idx}".encode()).hexdigest()
    bit_str = bin(int(seed, 16))[2:].zfill(256)
    return np.array([int(b) for b in bit_str[:n_bits]], dtype=np.uint8)


def fingerprint_from_ll(LL: np.ndarray, q_ll: float, row_idx: int, col_idx: int) -> np.ndarray:
    """
    256-bit fingerprint: parity of the quantised LL (step q_ll), XORed with the position salt.
    It changes GRADUALLY as the block content changes, so it can be measured with BER.
    """
    raw = (np.round(LL.flatten() / q_ll).astype(np.int64) % 2).astype(np.uint8)
    return raw ^ position_salt(row_idx, col_idx, len(raw))


def block_certificate(LL: np.ndarray, q_ll: float) -> str:
    """
    SHA-256 of the quantised LL. For reporting and signing only, NOT for the valid/invalid
    decision (the avalanche effect makes exact matching far too brittle).
    """
    quantised = np.round(LL / q_ll).astype(np.int32)
    return hashlib.sha256(quantised.tobytes()).hexdigest()


def ber(bits_a: np.ndarray, bits_b: np.ndarray) -> float:
    """Fraction of bits that differ between two bit arrays (0.0 to 1.0)."""
    assert len(bits_a) == len(bits_b), "Bit arrays must have the same length"
    return float(np.mean(bits_a != bits_b))
