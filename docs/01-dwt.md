# 1. DWT: splitting an image into coarse and fine

The **DWT** (Discrete Wavelet Transform) splits an image into four parts, each half the size of the original:

| Part | Contains | Behaviour |
|---|---|---|
| **LL** | the coarse shape (local average brightness) | holds almost all of the image content, usually the most stable under compression |
| **LH**, **HL**, **HH** | fine detail: horizontal edges, vertical edges, diagonals | small values, more sensitive to change |

This repo uses a one-level **Haar** wavelet on 32x32 blocks, so each part is 16x16.

## Try it

```python
from wm import dwt, imaging as im

bgr = im.sample_image(512)
Y = im.luminance(bgr)            # brightness channel (Y)
block = Y[0:32, 0:32]            # one 32x32 block

LL, LH, HL, HH = dwt.decompose(block)
print(LL.shape)                  # (16, 16)

back = dwt.reconstruct(LL, LH, HL, HH)
print((back == block).all())     # True: the DWT is invertible with no loss
```

On the bundled synthetic image the mean absolute value of LL is about 185, while LH, HL and HH are only about 3 to 4.
That means almost all of the content sits in LL. This number is specific to a smooth synthetic image, not a rule
for all photos.

## Why the DWT is used here

1. **It is invertible.** After embedding the mark, the image is rebuilt with the inverse DWT.
2. **It separates roles.** LL is used to compute the block fingerprint (because it is relatively stable), while HL is
   where the fingerprint is stored (because small changes there are almost invisible).
3. **It matches the block size.** A 32x32 block gives LL and HL of 16x16 = 256 coefficients each, equal to the
   256-bit fingerprint length. So 1 HL coefficient carries exactly 1 bit.

Reasons 1 and 2 are general properties of the DWT (see Mallat, *A Wavelet Tour of Signal Processing*). How well LL
survives a particular compression still has to be measured on the channel you care about.

Related work using the DWT for watermarking: Taj et al. (hybrid DWT and DCT, medical images). Full references
are in the [README](../README.md#related-work-and-credits).

Code: [`wm/dwt.py`](../wm/dwt.py). Next: [2. BER](02-ber.md).
