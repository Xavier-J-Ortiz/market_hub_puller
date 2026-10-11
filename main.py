"""Pull Market Hub Data for market arbitrage usage."""

from fetch_parse import fetch_region_orders, parse_region_orders

MARKETS = {
    # "The Forge": 10000002,
    # "Domain": 10000043,
    # "Heimatar": 10000030,
    "Sinq Laison": 10000032,
    "Metropoiis": 10000042,
}


def main():
    """Fetch regional market orders and screen for arbitrage opportunities."""
    for market, id in MARKETS.items():
        region_order_response = fetch_region_orders(id)
        region_orders = parse_region_orders(region_order_response)
        print(region_orders)
        print(
            f"Fetched all {market} market orders. There are {len(region_orders)}, which is of type "
            f"{type(region_orders)}, and it's first element is of type {type(region_orders[0])}."
        )


if __name__ == "__main__":
    main()
