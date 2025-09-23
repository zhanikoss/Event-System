import streamlit as st
import os, sys

# --- Fix imports (make sure "core" is visible) ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.transforms import load_seed, average_price


# --- Helpers for sales stats ---
def total_sold_tickets(orders) -> int:
    """Return total number of tickets sold (sum of items in all orders)."""
    total = 0
    for o in orders:
        for item in o.items:
            total += item.qty
    return total


def total_discounts(orders) -> float:
    """Dummy example: count cancelled orders as 'discounts'."""
    return sum(1 for o in orders if o.status == "cancelled")


# --- Load data ---
seed_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "data", "seed.json")
)
venues, halls, events, zones, ticket_types, prices, orders, quotas = load_seed(seed_path)


# --- Streamlit UI ---
st.set_page_config(page_title="Event Management Dashboard", layout="wide")

st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to:", ["Overview", "Events", "Tickets", "Orders"])


if page == "Overview":
    st.title("📊 Event System Overview")

    st.write("**General statistics:**")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Venues", len(venues))
    with col2:
        st.metric("Halls", len(halls))
    with col3:
        st.metric("Events", len(events))

    st.write("**Ticket statistics:**")
    col4, col5, col6 = st.columns(3)
    with col4:
        st.metric("Ticket Types", len(ticket_types))
    with col5:
        st.metric("Zones", len(zones))
    with col6:
        st.metric("Quotas", len(quotas))

    st.write("**Sales statistics:**")
    col7, col8, col9 = st.columns(3)
    with col7:
        avg_price = average_price(tuple(prices))
        st.metric("Average Ticket Price", f"{avg_price:.2f} ₸")
    with col8:
        sold = total_sold_tickets(orders)
        st.metric("Total Tickets Sold", sold)
    with col9:
        discount = total_discounts(orders)
        st.metric("Total Discounts", discount)


elif page == "Events":
    st.title("🎭 Events")
    for e in events:
        st.subheader(e.title)
        st.write(f"ID: {e.id}")
        st.write(f"Hall: {e.hall_id}")
        st.write(f"Start: {e.start} → End: {e.end}")


elif page == "Tickets":
    st.title("🎟️ Ticket Types")
    for t in ticket_types:
        st.subheader(t.title)
        st.write(f"ID: {t.id}")
        st.write(f"Refundable: {'Yes' if t.refundable else 'No'}")

    st.write("**Ticket Prices:**")
    for p in prices:
        st.write(f"- {p.amount} ₸ (Ticket type {p.ticket_type_id})")


elif page == "Orders":
    st.title("🛒 Orders")
    for o in orders:
        st.subheader(f"Order {o.id}")
        st.write(f"Event ID: {o.event_id}")
        st.write(f"Status: {o.status}")
        st.write(f"Total: {o.total} ₸")
        st.write("Items:")
        for it in o.items:
            st.write(f" - TicketType {it.ticket_type_id} × {it.qty}")