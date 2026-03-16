#!/usr/bin/env python3
import sys
import traceback

import processing.csv as df
from config import region_hubs

region_hubs


def main() -> None:
    try:
        _ = df.create_actionable_data()
        print("Actionable Data Created Successfully")
        sys.exit(0)
    except Exception as e:
        traceback.print_exc()
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
