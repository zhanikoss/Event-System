import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import streamlit as st
from core.transforms import load_seed, ticket_titles_upper, vip_tickets, discounted_prices, max_price, average_price, available_quotas

seed_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "seed.json"))
venues, halls, events, zones, ticket_types, prices, orders, quotas = load_seed(seed_path)

st.title("Event System")

# Overview — по требованиям лабы
st.header("Overview")
st.write(f"Venues: {len(venues)}")
st.write(f"Events: {len(events)}") 
st.write(f"Ticket types: {len(ticket_types)}")
st.write(f"Average price: {average_price(prices):.0f} KZT")
st.write(f"Available quotas: {len(available_quotas(quotas))}")

# Functional Core 
st.header("Ticket titles ")
for title in ticket_titles_upper(ticket_types):
    st.write(f"• {title}")

st.header("VIP tickets")
vip_list = vip_tickets(ticket_types)
if vip_list:
    for ticket in vip_list:
        st.write(f"• {ticket.title}")
else:
    st.write("No VIP tickets")

st.header("Discounted prices (10% off)")
discounted = discounted_prices(prices)
for i, price in enumerate(discounted, 1):
    st.write(f"{i}. {price} KZT")

st.header("Max price")
st.write(f"{max_price(prices)} KZT")

# Available quotas details
st.header("Available Quotas Details")
available = available_quotas(quotas)
if available:
    for quota in available:
        ticket = next((t for t in ticket_types if t.id == quota["ticket_type_id"]), None)
        if ticket:
            st.write(f"• {ticket.title}: {quota['available']} available")
else:
    st.write("No available quotas")