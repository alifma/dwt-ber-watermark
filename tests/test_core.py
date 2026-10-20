import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import json  # noqa: E402

import cv2  # noqa: E402

import verify_image  # noqa: E402
from wm import embed, imaging as im, robust_id, signing, verify  # noqa: E402

ID = 123456789


def _prepare():
    bgr = im.sample_image(256)
    Y_wm, cert = embed.embed_luminance(im.luminance(bgr), enrollment_id=ID)
    return bgr, im.replace_luminance(bgr, Y_wm), cert


def test_intact_all_blocks_valid():
    _, wm, _ = _prepare()
    assert verify.verify_luminance(im.luminance(wm))["percent_valid"] == 100.0


def test_image_without_watermark_is_rejected():
    bgr, _, _ = _prepare()
    assert verify.verify_luminance(im.luminance(bgr))["percent_valid"] < 5.0


def test_jpeg90_still_valid_and_id_readable():
    _, wm, _ = _prepare()
    j = im.jpeg(wm, 90)
    assert verify.verify_luminance(im.luminance(j))["percent_valid"] > 95.0
    assert robust_id.extract_id(im.luminance(j))[0] == ID


def test_local_edit_detected_and_localised():
    _, wm, _ = _prepare()
    r = verify.verify_luminance(im.luminance(im.local_edit(wm, 2, 2)))
    assert (~r["valid_map"])[2:4, 2:4].all()
    assert (~r["valid_map"]).sum() <= 8


def test_splicing_detected():
    _, wm, _ = _prepare()
    r = verify.verify_luminance(im.luminance(im.splice(wm, (0, 0), (5, 5))))
    assert not r["valid_map"][5, 5]


def test_signature():
    _, _, cert = _prepare()
    pub, priv = signing.generate_keys()
    info = signing.sign_certificates(cert, priv)
    assert signing.verify(cert, info, pub)["valid"]
    forged = dict(cert, **{"0_0": "0" * 64})
    assert not signing.verify(forged, info, pub)["valid"]
    other_pub, _ = signing.generate_keys()
    assert not signing.verify(cert, info, other_pub)["valid"]


def test_full_check_with_record(tmp_path):
    _, wm, cert = _prepare()
    pub, priv = signing.generate_keys()
    record = signing.build_record(ID, cert, signing.sign_certificates(cert, priv), pub)
    rec_path = tmp_path / "record.json"
    rec_path.write_text(json.dumps(record))

    def run(img):
        p = tmp_path / "img.png"
        cv2.imwrite(str(p), img)
        return verify_image.check(str(p), str(rec_path))

    good = run(im.jpeg(wm, 90))
    assert good["id_matches"] and good["signature_valid"] and good["percent_valid"] > 95.0

    edited = run(im.local_edit(wm, 2, 2))
    assert edited["signature_valid"] and edited["invalid_blocks"]

    record["certificates"]["0_0"] = "0" * 64  # record tampered with
    rec_path.write_text(json.dumps(record))
    assert not run(wm)["signature_valid"]
