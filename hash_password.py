from __future__ import annotations

import argparse
from getpass import getpass

from .security import hash_password


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate bcrypt hash for PhotoBridge users")
    parser.add_argument(
        "--password",
        "-p",
        help="Plain password to hash (omit to be prompted securely)",
    )
    args = parser.parse_args()
    plain = args.password or getpass("Enter password to hash: ")
    if not plain:
        raise SystemExit("Password cannot be empty.")
    if len(plain) > 72:
        print("Warning: bcrypt hashes only first 72 bytes; password will be truncated.")
    print(hash_password(plain))


if __name__ == "__main__":
    main()

