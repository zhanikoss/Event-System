import streamlit as st
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.transforms import load_seed, average_price, get_ticket_price
from core.auth import authenticate_user, is_admin
from core.domain import Venue, CartItem

# Настройка страницы
st.set_page_config(
    page_title="🎭 Event Management System", 
    page_icon="🎭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Красивый CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        background: linear-gradient(45deg, #FF6B6B, #4ECDC4);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 2rem;
        font-weight: bold;
    }
    .section-header {
        font-size: 2rem;
        color: #2c3e50;
        border-bottom: 3px solid #3498db;
        padding-bottom: 0.5rem;
        margin: 2rem 0 1rem 0;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 15px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .event-card {
        background: white;
        padding: 1.5rem;
        margin: 1rem 0;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        border-left: 5px solid #FF6B6B;
    }
    .ticket-card {
        background: #f8f9fa;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 10px;
        border: 1px solid #dee2e6;
    }
    .admin-card {
        background: #fff3cd;
        padding: 1rem;
        border-radius: 10px;
        border: 2px solid #ffeaa7;
        margin: 0.5rem 0;
    }
    .cart-item {
        background: #e8f4fd;
        padding: 0.8rem;
        margin: 0.5rem 0;
        border-radius: 8px;
        border-left: 4px solid #3498db;
    }
    .stButton button {
        background-color: #3498db;
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

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
        st.error(f"Error loading data: {e}")

# Инициализация
if 'user' not in st.session_state:
    st.session_state.user = None
if 'cart' not in st.session_state:
    st.session_state.cart = []

# Вспомогательная функция для получения названия билета
def get_ticket_display_name_safe(ticket_type_id):
    """Безопасная версия функции получения названия билета"""
    try:
        ticket_type = next((t for t in st.session_state.ticket_types if t.id == ticket_type_id), None)
        if not ticket_type:
            return f"Ticket {ticket_type_id}"
        
        event = next((e for e in st.session_state.events if e.id == ticket_type.event_id), None)
        event_name = event.title if event else "Unknown Event"
        
        return f"{ticket_type.title} - {event_name}"
    except:
        return f"Ticket {ticket_type_id}"

# Авторизация
def login_section():
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🔐 Authentication")
    
    if st.session_state.user:
        role_icon = "👑" if st.session_state.user.role == "admin" else "👤"
        st.sidebar.success(f"{role_icon} Welcome, {st.session_state.user.username}!")
        
        if st.sidebar.button("🚪 Logout", key="logout_btn", use_container_width=True):
            st.session_state.user = None
            st.session_state.cart = []
            st.rerun()
    else:
        with st.sidebar.form("login_form"):
            username = st.text_input("👤 Username")
            password = st.text_input("🔒 Password", type="password")
            
            if st.form_submit_button("🎯 Login", use_container_width=True):
                user = authenticate_user(username, password)
                if user:
                    st.session_state.user = user
                    st.rerun()
                else:
                    st.error("❌ Invalid credentials!")

# Корзина - ИСПРАВЛЕННАЯ ВЕРСИЯ
def cart_section():
    if st.session_state.user and st.session_state.cart:
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 🛒 Shopping Cart")
        
        total = 0
        for i, item in enumerate(st.session_state.cart):
            try:
                # Безопасное получение цены
                price = get_ticket_price(item.ticket_type_id, st.session_state.prices)
                display_name = get_ticket_display_name_safe(item.ticket_type_id)
                
                st.sidebar.markdown(f'<div class="cart-item">', unsafe_allow_html=True)
                st.sidebar.write(f"**{display_name}**")
                st.sidebar.write(f"Qty: {item.qty} × {price:,} ₸")
                st.sidebar.markdown('</div>', unsafe_allow_html=True)
                
                # Кнопка удаления
                if st.sidebar.button(f"🗑️ Remove", key=f"cart_remove_{i}"):
                    st.session_state.cart.pop(i)
                    st.rerun()
                
                total += item.qty * price
                st.sidebar.markdown("---")
                
            except Exception as e:
                st.sidebar.error(f"Error with item {i}")
                continue
        
        if total > 0:
            st.sidebar.markdown(f"**💰 Total: {total:,} ₸**")
            if st.sidebar.button("💳 Checkout", key="checkout_btn", use_container_width=True):
                st.sidebar.success("🎉 Order placed successfully!")
                st.session_state.cart = []
                st.rerun()
    elif st.session_state.user:
        st.sidebar.markdown("---")
        st.sidebar.info("🛒 Your cart is empty")

# Страницы
def overview_page():
    st.markdown('<div class="main-header">🎭 Event Management System</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="section-header">📊 System Overview</div>', unsafe_allow_html=True)
    
    overview_col1, overview_col2, overview_col3, overview_col4 = st.columns(4)
    
    with overview_col1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("🏛️ Venues", len(st.session_state.venues))
        st.markdown('</div>', unsafe_allow_html=True)
    
    with overview_col2:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("🎪 Events", len(st.session_state.events))
        st.markdown('</div>', unsafe_allow_html=True)
    
    with overview_col3:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("🎫 Ticket Types", len(st.session_state.ticket_types))
        st.markdown('</div>', unsafe_allow_html=True)
    
    with overview_col4:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        avg_price = average_price(st.session_state.prices)
        st.metric("💰 Avg Price", f"{avg_price:,.0f} ₸")
        st.markdown('</div>', unsafe_allow_html=True)

def events_page():
    st.markdown('<div class="section-header">🎪 All Events</div>', unsafe_allow_html=True)
    
    for event in st.session_state.events:
        venue = next((v for v in st.session_state.venues 
                     if v.id == next((h.venue_id for h in st.session_state.halls if h.id == event.hall_id), None)), None)
        
        st.markdown(f"""
        <div class="event-card">
            <h3>🎭 {event.title}</h3>
            <p>📅 <strong>Date:</strong> {event.start} to {event.end}</p>
            <p>🏟️ <strong>Venue:</strong> {venue.
name if venue else 'Unknown'} | 📍 {venue.city if venue else 'Unknown'}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Добавляем кнопки для добавления в корзину
        event_tickets = [t for t in st.session_state.ticket_types if t.event_id == event.id]
        if event_tickets and st.session_state.user:
            st.write("**Available tickets:**")
            for ticket in event_tickets:
                price = get_ticket_price(ticket.id, st.session_state.prices)
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"🎫 {ticket.title} - {price:,} ₸")
                with col2:
                    if st.button("🛒 Add to cart", key=f"add_{ticket.id}"):
                        cart_item = CartItem(
                            id=f"cart_{len(st.session_state.cart)}_{ticket.id}",
                            ticket_type_id=ticket.id,
                            qty=1
                        )
                        st.session_state.cart.append(cart_item)
                        st.success(f"Added {ticket.title} to cart!")
                        st.rerun()
        
        st.markdown("---")

def tickets_page():
    st.markdown('<div class="section-header">🎫 Available Tickets</div>', unsafe_allow_html=True)
    
    for ticket in st.session_state.ticket_types:
        event = next((e for e in st.session_state.events if e.id == ticket.event_id), None)
        zone = next((z for z in st.session_state.zones if z.id == ticket.zone_id), None)
        price = get_ticket_price(ticket.id, st.session_state.prices)
        
        st.markdown(f"""
        <div class="ticket-card">
            <h4>🎫 {ticket.title}</h4>
            <p>🎭 <strong>Event:</strong> {event.title if event else 'Unknown'}</p>
            <p>📍 <strong>Zone:</strong> {zone.name if zone else 'Unknown'}</p>
            <p>💰 <strong>Price:</strong> {price:,} ₸ | 🔄 <strong>Refundable:</strong> {'🟢 Yes' if ticket.refundable else '🔴 No'}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Кнопка добавления в корзину
        if st.session_state.user:
            if st.button("🛒 Add to Cart", key=f"ticket_add_{ticket.id}"):
                cart_item = CartItem(
                    id=f"cart_{len(st.session_state.cart)}_{ticket.id}",
                    ticket_type_id=ticket.id,
                    qty=1
                )
                st.session_state.cart.append(cart_item)
                st.success(f"Added {ticket.title} to cart!")
                st.rerun()

def admin_page():
    st.markdown('<div class="section-header">👨‍💼 Admin Panel</div>', unsafe_allow_html=True)
    
    # Управление площадками
    st.markdown("### 🎪 Manage Venues")
    
    admin_col1, admin_col2 = st.columns(2)
    
    with admin_col1:
        st.markdown("#### ➕ Add New Venue")
        with st.form("add_venue_form"):
            new_id = st.text_input("Venue ID*")
            new_name = st.text_input("Venue Name*")
            new_city = st.text_input("City*")
            
            if st.form_submit_button("🎯 Add Venue", use_container_width=True):
                if new_id and new_name and new_city:
                    new_venue = Venue(id=new_id, name=new_name, city=new_city)
                    st.session_state.venues.append(new_venue)
                    st.success("✅ Venue added successfully!")
                    st.rerun()
                else:
                    st.error("❌ Please fill all required fields!")
    
    with admin_col2:
        st.markdown("#### 📋 Existing Venues")
        if not st.session_state.venues:
            st.info("ℹ️ No venues available. Add your first venue!")
        else:
            for i, venue in enumerate(st.session_state.venues):
                venue_col1, venue_col2 = st.columns([3, 1])
                with venue_col1:
                    st.markdown(f"""
                    <div class="admin-card">
                        <strong>🏛️ {venue.name}</strong><br>
                        📍 {venue.city} | 🆔 {venue.id}
</div>
                    """, unsafe_allow_html=True)
                with venue_col2:
                    if st.button("🗑️ Delete", key=f"admin_del_venue_{i}"):
                        st.session_state.venues.pop(i)
                        st.rerun()

# Основное приложение
st.sidebar.markdown("# 🎭 Event System")
login_section()
cart_section()

st.sidebar.markdown("---")
st.sidebar.markdown("## 🧭 Navigation")

# Определяем доступные страницы
pages = ["🏠 Overview", "🎪 Events", "🎫 Tickets"]
if st.session_state.user and is_admin(st.session_state.user):
    pages.append("👨‍💼 Admin")

page = st.sidebar.radio("Go to:", pages, key="nav_radio")

# Определяем какая страница выбрана
if "🏠" in page:
    overview_page()
elif "🎪" in page:
    events_page()
elif "🎫" in page:
    tickets_page()
elif "👨‍💼" in page:
    admin_page()
