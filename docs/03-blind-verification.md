# 3. Verification without the original image (*blind*)

Many schemes need the original photo as a reference. But someone who receives a photo through WhatsApp usually has
only **one file**: the already-compressed photo itself.

The scheme in this repo checks a photo **without needing the original**, because the photo carries two things at once:

```
          received photo
                 |
          DWT per block
           /            \
        LL               HL
  (image content)   (where the fingerprint was embedded)
        |                |
 recompute the      read the
 fingerprint        stored bits
        \                /
         compare -> BER -> valid / suspicious
```

1. From the **LL** of the received photo, the fingerprint is recomputed.
2. From the **HL** of the same photo, the bits that were embedded earlier are read.
3. The two bit sequences are compared with BER. If a block's content changed, LL changed, so the recomputed
   fingerprint no longer matches the bits in HL.

No original photo is used at any step.

## Try it

```python
from wm import embed, verify, imaging as im

bgr = im.sample_image(512)
Y_wm, certificates = embed.embed_luminance(im.luminance(bgr), enrollment_id=123456789)
received = im.replace_luminance(bgr, Y_wm)

# Verification uses only the received photo, not the original `bgr`.
result = verify.verify_luminance(im.luminance(received))
print(result["percent_valid"])                   # 100.0

edited = im.local_edit(received, 2, 2)           # edit 2x2 blocks
result = verify.verify_luminance(im.luminance(edited))
print((~result["valid_map"]).sum())              # 4 suspicious blocks, and where they are is known

plain = verify.verify_luminance(im.luminance(bgr))   # a photo with no watermark
print(plain["percent_valid"])                    # 0.0
```

## What this proves, and what it does not

This check only proves that **each block's content is consistent with the mark inside it**. It does not prove
**who published** the photo. The algorithm is public, so anyone can produce a photo whose mark looks valid.

That is why this repo has a second layer:

- A short, more compression-resistant ID is planted in LL (`wm/robust_id.py`), so the photo can be traced to its
  certificates.
- The certificates (SHA-256 of each block's LL) are signed with **ML-DSA-44** (`wm/signing.py`), so the publisher
  can be proven with a public key.

Run all three checks together with `python verify_image.py <image> outputs/record.json` (after `python demo.py`).
It reports the ID match, the signature result, and the suspicious blocks. Note that the signature vouches for the
publisher's **record**, not for the pixels: an image with no watermark still passes the signature step and fails the
ID and BER steps.

## Limitations

- **Edits smaller than one block can slip through.** Overwriting 24x24 pixels inside one 32x32 block stays below the
  threshold (BER 0.289); only 32x32 is detected (BER 0.492).
- **Resizing and geometric transforms** shift the block grid, so verification fails.
- **Heavy compression** causes false alarms on photos that are actually intact (see the table in [2. BER](02-ber.md)).
- The compression simulated here is plain JPEG, **not** a replica of WhatsApp compression.
- This is an implementation for learning and research, not a security product.

Previous: [2. BER](02-ber.md). Code: [`wm/verify.py`](../wm/verify.py), [`wm/embed.py`](../wm/embed.py).
