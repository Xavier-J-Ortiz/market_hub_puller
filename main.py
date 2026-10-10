"""Pull Market Hub Data for market arbitrage usage."""

from fetch_parse import fetch_region_orders, parse_region_orders


def main():
    """Fetch regional market orders and screen for arbitrage opportunities."""
    the_forge_id = 10000002
    jita_orders_response = fetch_region_orders(the_forge_id)
    jita_orders = parse_region_orders(jita_orders_response)
    print(jita_orders)
    print(
        f"There are {len(jita_orders)}, which is of type {type(jita_orders)}, and it's first \
                element is of type {type(jita_orders[0])}."
    )


if __name__ == "__main__":
    main()
