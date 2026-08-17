"""One-off: print a VAPID key pair for Web Push.

    python scripts/generate_vapid_keys.py

Paste the output into .env as VAPID_PUBLIC_KEY / VAPID_PRIVATE_KEY. Keys are
generated locally — no external account or API call needed.
"""

import base64

from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from py_vapid import Vapid


def _b64url(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def main():
    vapid = Vapid()
    vapid.generate_keys()

    public_raw = vapid.public_key.public_bytes(
        encoding=Encoding.X962,
        format=PublicFormat.UncompressedPoint,
    )
    private_raw = vapid.private_key.private_numbers().private_value.to_bytes(32, "big")

    print("VAPID_PUBLIC_KEY=%s" % _b64url(public_raw))
    print("VAPID_PRIVATE_KEY=%s" % _b64url(private_raw))


if __name__ == "__main__":
    main()
