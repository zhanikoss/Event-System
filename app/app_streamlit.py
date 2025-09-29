import streamlit as st
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.transforms import load_seed, average_price
from core.auth import authenticate_user, is_admin
from core.domain import Venue, CartItem

# Настройка страницы
st.set_page_config(page_title="Event System", layout="wide")

# Загрузка данных
if 'data_loaded' not in st.session_state:
    try:
        seed_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "seed.json"))
        data = load_seed(seed_path)
        st.session_state.users = data[0]
        st.session_state.venues = data[1]
        st.session_state.halls = data[2]
        st.session_state.events = data[3]
        st.session_state.zones = data[4]
        st.session_state.ticket_types = data[5]
        st.session_state.prices = data[6]
        st.session_state.orders = data[7]
        st.session_state.quotas = data[8]
        st.session_state.data_loaded = True
    except Exception as e:
        st.error(f"Error: {e}")

# Инициализация
if 'user' not in st.session_state:
    st.session_state.user = None
if 'cart' not in st.session_state:
    st.session_state.cart = []

# Простая авторизация
def login_section():
    st.sidebar.header("🔐 Login")
    if st.session_state.user:
        st.sidebar.success(f"Hello, {st.session_state.user.username}!")
        if st.sidebar.button("Logout"):
            st.session_state.user = None
            st.session_state.cart = []
            st.rerun()
    else:
        username = st.sidebar.text_input("Username")
        password = st.sidebar.text_input("Password", type="password")
        if st.sidebar.button("Login"):
            user = authenticate_user(username, password)
            if user:
                st.session_state.user = user
                st.rerun()
            else:
                st.sidebar.error("Wrong credentials")

# Простая корзина
def cart_section():
    if st.session_state.user and st.session_state.cart:
        st.sidebar.header("🛒 Cart")
        for item in st.session_state.cart:
            st.sidebar.write(f"Item: {item.ticket_type_id}, Qty: {item.qty}")
        if st.sidebar.button("Clear Cart"):
            st.session_state.cart = []
            st.rerun()

# Основные страницы
def overview_page():
    st.title("Event System Overview")
    st.write(f"Venues: {len(st.session_state.venues)}")
    st.write(f"Events: {len(st.session_state.events)}")
    st.write(f"Ticket Types: {len(st.session_state.ticket_types)}")
    
    avg = average_price(st.session_state.prices)
    st.write(f"Average Price: {avg:.0f} ₸")

def events_page():
    st.title("Events")
    for event in st.session_state.events:
        st.subheader(event.title)
        st.write(f"Date: {event.start}")
        st.write(f"Hall: {event.hall_id}")

def tickets_page():
    st.title("Tickets")
    for ticket in st.session_state.ticket_types:
        st.subheader(ticket.title)
        st.write(f"Event: {ticket.event_id}")
        st.write(f"Refundable: {ticket.refundable}")

def admin_page():
    st.title("Admin Panel")
    st.write("Add new venue:")
    with st.form("add_venue"):
        id = st.text_input("ID")
        name = st.text_input("Name")
        city = st.text_input("City")
        if st.form_submit_button("Add"):
            new_venue = Venue(id=id, name=name, city=city)
            st.session_state.venues.append(new_venue)
            st.success("Venue added!")
    
    st.write("Current venues:")
    for venue in st.session_state.venues:
        st.write(f"- {venue.name} ({venue.city})")

# Навигация и запуск
login_section()
cart_section()

st.sidebar.header("Menu")
pages = ["Overview", "Events", "Tickets"]
if st.session_state.user and is_admin(st.session_state.user):
    pages.append("Admin")

page = st.sidebar.radio("Go to:", pages)

if page == "Overview":
    overview_page()
elif page == "Events":
    events_page()
elif page == "Tickets":
    tickets_page()
elif page == "Admin":
    admin_page()