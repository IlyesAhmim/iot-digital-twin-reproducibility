#!/usr/bin/env python3
"""Per-message size overhead of source-side freshness evidence (configuration C1).

Encodes one telemetry update as plain CBOR (C0: value + gateway timestamp and
sequence number) and as a COSE_Sign1 / COSE_Mac0 object (RFC 9052) carrying the
source sequence number and generation timestamp under the signature or MAC.
Sizes are exact encodings; timings are for this host only and are NOT
representative of constrained devices (they are printed and saved in the JSON
output, but are not used as measurements in the paper).

Run:  python3 cose_overhead.py
"""
import hashlib
import hmac
import json
import time

import cbor2
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature

SEQ = 1_234_567                  # 32-bit sequence number
TS_MS = 1_793_000_000_000        # generation time in ms since the epoch (2026)
VALUE = 2.0371                   # vibration velocity, mm/s


def float32_payload():
    import struct
    # force a float32 encoding of the value (CBOR major type 7, additional info 26)
    m = bytearray(cbor2.dumps({1: SEQ, 2: TS_MS, 3: 0}, canonical=True))
    enc_val = b"\xfa" + struct.pack(">f", VALUE)
    return bytes(m[:-1]) + enc_val


def cose_sign1(pl, alg, sign):
    protected = cbor2.dumps({1: alg})
    sig_structure = cbor2.dumps(["Signature1", protected, b"", pl])
    sig = sign(sig_structure)
    msg = cbor2.CBORTag(18, [protected, {4: b"\x01"}, pl, sig])   # kid = 0x01
    return cbor2.dumps(msg), sig_structure, sig


def cose_mac0(pl, key):
    protected = cbor2.dumps({1: 4})          # HMAC 256/64
    mac_structure = cbor2.dumps(["MAC0", protected, b"", pl])
    tag = hmac.new(key, mac_structure, hashlib.sha256).digest()[:8]
    return cbor2.dumps(cbor2.CBORTag(17, [protected, {4: b"\x01"}, pl, tag]))


def main():
    pl = float32_payload()
    c0 = len(pl)
    ed = Ed25519PrivateKey.generate()
    s_ed, ss, sig = cose_sign1(pl, -8, ed.sign)
    p256 = ec.generate_private_key(ec.SECP256R1())

    def es256(data):
        der = p256.sign(data, ec.ECDSA(hashes.SHA256()))
        r, s = decode_dss_signature(der)
        return r.to_bytes(32, "big") + s.to_bytes(32, "big")

    s_es, _, _ = cose_sign1(pl, -7, es256)
    s_mac = cose_mac0(pl, b"k" * 32)
    out = {
        "C0_plain_CBOR_bytes": c0,
        "C1_COSE_Sign1_EdDSA_bytes": len(s_ed),
        "C1_COSE_Sign1_ES256_bytes": len(s_es),
        "C1_COSE_Mac0_HMAC256_64_bytes": len(s_mac),
    }
    out["overhead_EdDSA_bytes"] = out["C1_COSE_Sign1_EdDSA_bytes"] - c0
    out["overhead_ES256_bytes"] = out["C1_COSE_Sign1_ES256_bytes"] - c0
    out["overhead_HMAC_bytes"] = out["C1_COSE_Mac0_HMAC256_64_bytes"] - c0
    # host-only timing (informative)
    n = 2000
    t = time.perf_counter()
    for _ in range(n):
        ed.sign(ss)
    out["host_EdDSA_sign_us"] = round((time.perf_counter() - t) / n * 1e6, 1)
    pub = ed.public_key()
    t = time.perf_counter()
    for _ in range(n):
        pub.verify(sig, ss)
    out["host_EdDSA_verify_us"] = round((time.perf_counter() - t) / n * 1e6, 1)
    print(json.dumps(out, indent=1))
    with open("cose_overhead.json", "w") as f:
        json.dump(out, f, indent=1)


if __name__ == "__main__":
    main()
