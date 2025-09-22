from core.transforms import (
    load_seed, order_total, hold, release,
    ticket_titles_upper, vip_tickets, discounted_prices, max_price
)
from core.domain import CartItem


def main():
    venues, halls, events, zones, ticket_types, prices, orders, quotas = load_seed("data/seed.json")

    print("Venues count:", len(venues))
    print("Events count:", len(events))
    print("Ticket types count:", len(ticket_types))

    print("Ticket titles (uppercase):", ticket_titles_upper(ticket_types))
    print("VIP tickets:", [t.title for t in vip_tickets(ticket_types)])
    print("Discounted prices:", discounted_prices(prices))
    print("Max price:", max_price(prices))

    cart = ()
    cart = hold(cart, CartItem(id="1", ticket_type_id=ticket_types[0].id, qty=2))
    cart = hold(cart, CartItem(id="2", ticket_type_id=ticket_types[1].id, qty=1))
    print("Cart:", [(item.ticket_type_id, item.qty) for item in cart])

    total = order_total(prices, cart)
    print("Order total:", total)

    cart = release(cart, "1")
    print("Cart after removal:", [(item.ticket_type_id, item.qty) for item in cart])


if __name__ == "__main__":
    main()