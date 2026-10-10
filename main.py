"""Pull Market Hub Data for market arbitrage usage."""

from fetch_parse import fetch_region_orders


def main():
    """Fetch regional market orders and screen for arbitrage opportunities."""
    the_forge_id = 10000002
    raw_json = fetch_region_orders(the_forge_id)


if __name__ == "__main__":
    main()
