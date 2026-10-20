"""DWT utilities: decomposition, reconstruction, and coefficient position layout."""
import numpy as np
import pywt


def decompose(block: np.ndarray, wavelet: str = "haar"):
    """One-level DWT. Returns LL, LH, HL, HH as separate float64 arrays."""
    LL, (LH, HL, HH) = pywt.dwt2(block.astype(np.float64), wavelet)
    return LL, LH, HL, HH


def reconstruct(LL, LH, HL, HH, wavelet: str = "haar") -> np.ndarray:
    """Inverse DWT, rounded to uint8. The rounding is an unavoidable ~1 unit of noise."""
    rec = pywt.idwt2((LL, (LH, HL, HH)), wavelet)
    return np.clip(np.round(rec), 0, 255).astype(np.uint8)


def grid_positions(shape, n_bits: int = 256):
    """
    Spread n_bits positions evenly over the coefficient plane. When shape is exactly 16x16 and
    n_bits=256, every coefficient is used (1 bit per coefficient).
    """
    h, w = shape
    n_grid = int(round(np.sqrt(n_bits)))
    if n_grid * n_grid != n_bits:
        raise ValueError("n_bits must be a perfect square (e.g. 256 = 16x16)")
    rows = np.linspace(0, h - 1, n_grid, dtype=int)
    cols = np.linspace(0, w - 1, n_grid, dtype=int)
    return [(r, c) for r in rows for c in cols][:n_bits]
