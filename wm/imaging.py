"""Image helpers: read (Y only), synthetic sample image, JPEG, manipulations, and result overlay."""
import cv2
import numpy as np

from .config import BLOCK_SIZE


def sample_image(size: int = 512, seed: int = 7) -> np.ndarray:
    """Synthetic BGR image (gradients, shapes, noisy texture). Contains no personal data."""
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:size, 0:size].astype(np.float64)
    r = 90 + 110 * (x / size)
    g = 80 + 100 * (y / size)
    b = 120 + 60 * np.sin(x / 37.0) * np.cos(y / 53.0)
    img = np.stack([b, g, r], axis=-1)
    cv2.circle(img, (size // 3, size // 2), size // 6, (235, 235, 235), -1)
    cv2.rectangle(img, (size // 2, size // 5), (size - 60, size // 2), (40, 60, 200), -1)
    cv2.line(img, (0, size - 1), (size - 1, 0), (20, 20, 20), 9)
    # fine noise: flat blocks are prone to false alarms, so add photo-like texture
    img += rng.normal(0, 7, img.shape)
    return np.clip(img, 0, 255).astype(np.uint8)


def read_image(path: str):
    """Returns (bgr, Y). Grayscale images are supported too (bgr = Y)."""
    img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if img is None:
        raise FileNotFoundError(path)
    if img.ndim == 2:
        return img, img
    bgr = img[:, :, :3]
    return bgr, cv2.cvtColor(bgr, cv2.COLOR_BGR2YCrCb)[:, :, 0]


def replace_luminance(bgr: np.ndarray, Y_new: np.ndarray) -> np.ndarray:
    """Paste a new Y into the image; the original Cr/Cb are untouched (colour preserved)."""
    if bgr.ndim == 2:
        return Y_new
    ycrcb = cv2.cvtColor(bgr, cv2.COLOR_BGR2YCrCb)
    ycrcb[:, :, 0] = Y_new
    return cv2.cvtColor(ycrcb, cv2.COLOR_YCrCb2BGR)


def luminance(bgr: np.ndarray) -> np.ndarray:
    return bgr if bgr.ndim == 2 else cv2.cvtColor(bgr, cv2.COLOR_BGR2YCrCb)[:, :, 0]


def jpeg(bgr: np.ndarray, quality: int) -> np.ndarray:
    """Simulated JPEG recompression (encode then decode). Not an exact replica of WhatsApp compression."""
    ok, buf = cv2.imencode(".jpg", bgr, [cv2.IMWRITE_JPEG_QUALITY, quality])
    assert ok
    return cv2.imdecode(buf, cv2.IMREAD_UNCHANGED)


def local_edit(bgr: np.ndarray, row: int, col: int, size: int = 2) -> np.ndarray:
    """Local manipulation: overwrite a (size x size)-block area with a flat colour, like erasing an object."""
    out = bgr.copy()
    y0, x0 = row * BLOCK_SIZE, col * BLOCK_SIZE
    out[y0 : y0 + size * BLOCK_SIZE, x0 : x0 + size * BLOCK_SIZE] = (128, 140, 150)
    return out


def splice(bgr: np.ndarray, source: tuple, target: tuple) -> np.ndarray:
    """Copy one valid block from `source` (row, col) to `target` in the same image."""
    out = bgr.copy()
    sy, sx = source[0] * BLOCK_SIZE, source[1] * BLOCK_SIZE
    ty, tx = target[0] * BLOCK_SIZE, target[1] * BLOCK_SIZE
    out[ty : ty + BLOCK_SIZE, tx : tx + BLOCK_SIZE] = bgr[sy : sy + BLOCK_SIZE, sx : sx + BLOCK_SIZE]
    return out


def overlay(bgr: np.ndarray, valid_map: np.ndarray) -> np.ndarray:
    """Green (valid) / red (invalid) boxes over the image. Returns BGR."""
    out = bgr.copy() if bgr.ndim == 3 else cv2.cvtColor(bgr, cv2.COLOR_GRAY2BGR)
    for i in range(valid_map.shape[0]):
        for j in range(valid_map.shape[1]):
            color = (80, 200, 80) if valid_map[i, j] else (60, 60, 230)
            p1 = (j * BLOCK_SIZE, i * BLOCK_SIZE)
            p2 = ((j + 1) * BLOCK_SIZE - 1, (i + 1) * BLOCK_SIZE - 1)
            cv2.rectangle(out, p1, p2, color, 2 if not valid_map[i, j] else 1)
    return out
