from core.transforms import (
    load_seed, order_total, hold, release,
    order_total_with_discount, ticket_titles_upper,
    vip_tickets, discounted_prices, max_price
)
from core.domain import CartItem

def main():
    venues, halls, events, zones, ticket_types, prices, orders = load_seed("data/seed.json")

    print("Количество площадок:", len(venues))
    print("Количество событий:", len(events))
    print("Количество типов билетов:", len(ticket_types))

    print("Названия билетов (верхний регистр):", ticket_titles_upper(ticket_types))
    print("VIP билеты:", [t.title for t in vip_tickets(ticket_types)])
    print("Скидочные цены:", discounted_prices(prices))
    print("Максимальная цена:", max_price(prices))

    cart = ()
    cart = hold(cart, CartItem(id="1", ticket_type_id=ticket_types[0].id, qty=2))
    cart = hold(cart, CartItem(id="2", ticket_type_id=ticket_types[1].id, qty=1))
    print("Корзина:", cart)

    total = order_total(prices, cart)
    print("Общая сумма заказа:", total)

    total_discount = order_total_with_discount(prices, cart, (ticket_types[0].id,))
    print("Сумма со скидкой (первый билет):", total_discount)

    cart = release(cart, ticket_types[0].id)
    print("Корзина после удаления:", cart)

if __name__ == "__main__":
    main()
