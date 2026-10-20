"""Core scheme parameters. These values were calibrated empirically; change them with care."""

WAVELET = "haar"

# Spatial block size (pixels). With 32, the LL and HL sub-bands of each block are 16x16 = 256
# coefficients, exactly the fingerprint length (256), so 1 HL coefficient carries 1 bit.
BLOCK_SIZE = 32

# Fingerprint length per block (bits). Fixed at 256 (matches the SHA-256 length).
N_BITS = 256

# Strength of embedding a bit into an HL coefficient (parity QIM). Larger = more robust to
# compression, but PSNR drops.
Q_EMBED = 16.0

# Coarseness of the LL quantisation used to compute the fingerprint. Must be recalibrated if
# BLOCK_SIZE or the image type changes.
Q_LL_HASH = 48.0

# A block is valid when its BER (fraction of differing fingerprint bits) is <= this threshold.
BER_THRESHOLD = 0.30

# Robust ID layer in LL (see robust_id.py): QIM step and lattice offset.
Q_ID_LL = 16.0
ID_DITHER = 4.0
