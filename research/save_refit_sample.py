"""Save 10,000 complete readings from a downloaded REFIT byte-range prefix."""
import argparse
from pathlib import Path


def save_sample(prefix, destination):
    # The byte download can stop midway through a row. Keep only complete lines.
    lines = prefix.read_bytes().splitlines(keepends=True)
    selected = lines[:10001]  # One header plus 10,000 readings.
    if len(selected) != 10001 or not selected[-1].endswith(b"\n"):
        raise ValueError("Download does not contain 10,000 complete readings")
    if not selected[0].startswith(b"Time,Unix,Aggregate,"):
        raise ValueError("Download is not the expected REFIT CSV")
    # Exclusive creation protects any recording already at this destination.
    with destination.open("xb") as output:
        output.write(b"".join(selected))
    print(f"Saved 10,000 readings to {destination}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("prefix", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    save_sample(args.prefix, args.destination)
