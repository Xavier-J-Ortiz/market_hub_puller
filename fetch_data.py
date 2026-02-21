#!/usr/bin/env python3
import sys

import config
import processing.csv as df

region_hubs = config.region_hubs


def main():
    try:
        df.create_actionable_data()
        print("Actionable Data Created Successfully")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
