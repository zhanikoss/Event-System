import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from core.transforms import load_seed, ticket_titles_upper, vip_tickets, discounted_prices, max_price
from core.domain import CartItem

# путь к seed.json
seed_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "seed.json"))
venues, halls, events, zones, ticket_types, prices, orders = load_seed(seed_path)

st.title("Event System 🎟️")

# Площадки
st.header("Площадки")
for venue in venues:
    st.write(f"{venue.name}")

# События
st.header("События")
for event in events:
    st.write(f"{event.title}")

# Билеты
st.header("Ticket types with its original prices")
for t in ticket_types:
    price = next(p.amount for p in prices if p.ticket_type_id == t.id)
    st.write(f"{t.title.upper()} — {price} тг")

# VIP билеты
st.header("VIP билеты")
for vip in vip_tickets(ticket_types):
    st.write(vip.title)

# Скидочные цены
st.header("Скидочные цены")
st.write(discounted_prices(prices))

# Максимальная цена
st.header("Максимальная цена")
st.write(max_price(prices))

# Простая корзина
st.header("Корзина")
cart = ()
cart = cart + (CartItem(id="1", ticket_type_id=ticket_types[0].id, qty=2),)
cart = cart + (CartItem(id="2", ticket_type_id=ticket_types[1].id, qty=1),)
st.write(cart)

def order_total(prices, cart):
    return sum(next(p.amount for p in prices if p.ticket_type_id == c.ticket_type_id) * c.qty for c in cart)

total = order_total(prices, cart)
st.write(f"Общая сумма заказа: {total}")
