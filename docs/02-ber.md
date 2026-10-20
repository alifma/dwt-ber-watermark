# 2. BER: not "same or different?", but "how different?"

**BER** (Bit Error Rate) is the percentage of bits that differ between two bit sequences.

```
sequence A : 1 0 1 1 0 0 1 0 1 1 ...   (100 bits)
sequence B : 0 0 1 0 0 1 1 0 1 1 ...   (100 bits)
20 bits differ  ->  BER = 20 / 100 = 0.2
```

```python
import numpy as np
from wm import fingerprint as fp

a = np.random.default_rng(1).integers(0, 2, 100)
b = a.copy()
b[:20] ^= 1                  # flip 20 bits
print(fp.ber(a, b))          # 0.2
```

- BER 0 means identical.
- BER around 0.5 means unrelated (the same as random guessing).

## Why not just use a hash

A hash such as SHA-256 only answers "same or different". Change one pixel and the hash changes completely (the
*avalanche effect*), so a photo that was merely compressed and a photo that was edited both come out as "no match".

The fingerprint in this repo is built from the quantised LL (`wm/fingerprint.py`). When a block's content changes a
little, only a few bits flip, so the difference can be **measured** with BER and given a threshold.

## The per-block threshold

The image is cut into 32x32 blocks and each block gets its own BER. A block is **valid** when BER <= `0.30`
(`BER_THRESHOLD` in [`wm/config.py`](../wm/config.py)) and **suspicious** when it is higher.

Some numbers from a synthetic 512x512 image (256 blocks) with a fixed seed:

| Condition | Valid blocks | Mean BER |
|---|---|---|
| Intact | 100% | 0.000 |
| JPEG quality 90 | 100% | 0.024 |
| JPEG quality 80 | 99.6% | 0.192 |
| JPEG quality 70 | 37.5% | 0.311 |
| No watermark | 0% | 0.498 |
| Edited (2x2 blocks) | 98.4% (4 blocks suspicious) | 0.008 |

Note JPEG 70: heavy compression makes many blocks that are actually intact look suspicious. That is a false alarm,
and the 0.30 threshold has to be recalibrated for each channel. These numbers come from a single synthetic image and
are not general results.

BER is a common way to measure how well an extracted watermark survived an attack; for example Taj et al. (2026)
report it for noise and JPEG. Here it is used per block as a tamper threshold instead. References are in the
[README](../README.md#related-work-and-credits).

Code: [`wm/fingerprint.py`](../wm/fingerprint.py), [`wm/verify.py`](../wm/verify.py).
Previous: [1. DWT](01-dwt.md). Next: [3. Blind verification](03-blind-verification.md).
