import streamlit as st
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.transforms import load_seed, average_price, get_ticket_display_name, get_ticket_price, validate_order
from core.auth import authenticate_user, is_admin
from core.domain import Venue, CartItem
from core.filters import by_city, by_date_range, by_price_range, compose_filters
from core.recursion import flatten_zone_tree, expand_seatmap, get_zone_hierarchy, calculate_total_seats
import json
from core.filters import by_city, by_date_range, by_price_range, compose_filters
from core.recursion import flatten_zone_tree, expand_seatmap, get_zone_hierarchy, calculate_total_seats
from core.memo import quote_tickets, benchmark_quotes
from core.compose import create_order_pipeline
from core.lazy import lazy_gate_flow, iter_orders, simulate_scan_stream
from datetime import datetime
# Настройка страницы
st.set_page_config(
    page_title= "Event Management System", 
    page_icon="🎫",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Подключаем CSS-файл
with open(os.path.join(os.path.dirname(__file__), "style.css")) as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


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
        st.session_state.admission_gates = data[9] if len(data) > 9 else []
        st.session_state.scans = data[10] if len(data) > 10 else []
        st.session_state.event_msgs = data[11] if len(data) > 11 else []
        st.session_state.rules = data[12] if len(data) > 12 else []  # ← ДОБАВЬ ЭТУ СТРОЧКУ!
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
    """🛒 Отображает корзину, подсчёт суммы и оформление заказа с глобальными событиями"""
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🛒 Shopping Cart")
    
    # Импортируем глобальную шину событий
    from core.frp import event_bus
    from datetime import datetime
    import time

    if st.session_state.user and st.session_state.cart:
        total = 0
        cart_items_details = []

        # Сначала собираем всю информацию о товарах в корзине
        for i, item in enumerate(st.session_state.cart):
            try:
                price = get_ticket_price(item.ticket_type_id, st.session_state.prices)
                display_name = get_ticket_display_name_safe(item.ticket_type_id)
                item_total = item.qty * price
                total += item_total
                
                cart_items_details.append({
                    "index": i,
                    "item": item,
                    "price": price,
                    "display_name": display_name,
                    "item_total": item_total
                })
                
            except Exception as e:
                st.sidebar.error(f"Error with item {i}: {e}")
                continue

        # Отображаем все товары в корзине
        for detail in cart_items_details:
            i, item, price, display_name, item_total = (
                detail["index"], detail["item"], detail["price"], 
                detail["display_name"], detail["item_total"]
            )
            
            st.sidebar.markdown(
                f"""
                <div style="border: 1px solid #e0e0e0; border-radius: 8px; padding: 12px; margin: 8px 0;">
                    <div style="font-weight: bold;">🎟 {display_name}</div>
                    <div>Qty: {item.qty} × {price:,} ₸</div>
                    <div style="font-weight: bold; color: #2196F3;">Subtotal: {item_total:,} ₸</div>
                </div>
                """, 
                unsafe_allow_html=True
            )

            # Кнопка удаления - публикуем в ГЛОБАЛЬНУЮ шину
            if st.sidebar.button(f"🗑 Remove", key=f"cart_remove_{i}"):
                # ✅ ГЕНЕРИРУЕМ ГЛОБАЛЬНОЕ СОБЫТИЕ CANCELLED
                event_bus.publish("CANCELLED", {
                    "cart_item_id": item.id,
                    "ticket_type_id": item.ticket_type_id,
                    "quantity": item.qty,
                    "display_name": display_name,
                    "reason": "user_removed_from_cart",
                    "user_id": st.session_state.user.id,
                    "timestamp": datetime.now().isoformat()
                })
                
                st.session_state.cart.pop(i)
                st.sidebar.success(f"Removed {display_name} from cart!")
                st.rerun()

        # Итоговая сумма и оформление заказа
        if total > 0:
            st.sidebar.markdown("---")
            st.sidebar.markdown(
                f"""
                <div style="background: #e3f2fd; padding: 12px; border-radius: 8px;">
                    <div style="font-size: 1.2em; font-weight: bold; text-align: center;">
                        💰 Total: {total:,} ₸
                    </div>
                </div>
                """, 
                unsafe_allow_html=True
            )

            # Информация о пользователе
            st.sidebar.markdown("---")
            st.sidebar.markdown("#### 👤 Order Information")
            
            user_age = st.sidebar.number_input(
                "🎂 Your age", 
                min_value=0, 
                max_value=120, 
                step=1,
                value=25,
                help="Required for age-restricted events"
            )

            # Кнопка оформления заказа
            if st.sidebar.button(
                "💳 Checkout & Purchase", 
                key="checkout_btn", 
                use_container_width=True,
                type="primary"
            ):
                from core.compose import create_order_pipeline

                # ✅ ИСПРАВЛЕНИЕ: используем st.spinner() вместо st.sidebar.spinner()
                with st.spinner("🔄 Processing your order..."):
                    # ✅ ГЕНЕРИРУЕМ ГЛОБАЛЬНОЕ СОБЫТИЕ HOLD (бронирование)
                    hold_items = []
                    for detail in cart_items_details:
                        hold_items.append({
                            "ticket_type_id": detail["item"].ticket_type_id,
                            "display_name": detail["display_name"],
                            "quantity": detail["item"].qty,
                            "unit_price": detail["price"],
                            "subtotal": detail["item_total"]
                        })
                    
                    event_bus.publish("HOLD", {
                        "order_id": f"pending_{int(time.time())}",
                        "items": hold_items,
                        "total_amount": total,
                        "user_id": st.session_state.user.id,
                        "user_age": user_age,
                        "timestamp": datetime.now().isoformat(),
                        "status": "hold_placed"
                    })
                    
                    # Создаем заказ через пайплайн
                    result = create_order_pipeline(
                        tuple(st.session_state.cart),
                        tuple(st.session_state.ticket_types),
                        tuple(st.session_state.quotas),
                        tuple(st.session_state.rules),
                        tuple(st.session_state.prices),
                    )

                # Обрабатываем результат
                if hasattr(result, "value"):
                    order = result.value

                    # Проверка возрастного ограничения
                    if user_age < 18:
                        st.sidebar.error("🚫 You must be at least 18 years old to complete this purchase.")
                        
                        # ✅ ГЕНЕРИРУЕМ ГЛОБАЛЬНОЕ СОБЫТИЕ CANCELLED
                        event_bus.publish("CANCELLED", {
                            "order_id": order.id,
                            "reason": "age_restriction_failed",
                            "required_age": 18,
                            "user_age": user_age,
                            "total_amount": total,
                            "timestamp": datetime.now().isoformat()
                        })
                    else:
                        # ✅ ГЕНЕРИРУЕМ ГЛОБАЛЬНОЕ СОБЫТИЕ PURCHASED
                        purchased_items = []
                        for detail in cart_items_details:
                            purchased_items.append({
                                "ticket_type_id": detail["item"].ticket_type_id,
                                "display_name": detail["display_name"],
                                "quantity": detail["item"].qty,
                                "unit_price": detail["price"]
                            })
                        
                        event_bus.publish("PURCHASED", {
                            "order_id": order.id,
                            "event_id": order.event_id,
                            "items": purchased_items,
                            "total_amount": order.total,
                            "currency": "KZT",
                            "user_id": st.session_state.user.id,
                            "user_age": user_age,
                            "timestamp": datetime.now().isoformat(),
                            "status": "payment_confirmed"
                        })
                        
                        # Создаем заказ в системе
                        from core.domain import Order
                        paid_order = Order(
                            id=order.id,
                            event_id=order.event_id,
                            items=order.items,
                            total=order.total,
                            status="paid"
                        )
                        
                        # Обновляем состояние заказов
                        updated_orders = list(st.session_state.orders)
                        updated_orders.append(paid_order)
                        st.session_state.orders = tuple(updated_orders)
                        
                        # Сохраняем новые заказы для отображения
                        if 'new_orders' not in st.session_state:
                            st.session_state.new_orders = []
                        st.session_state.new_orders.append(paid_order)
                        
                        # Показываем успешное сообщение
                        st.sidebar.success(
                            f"""
                            ✅ Order Created Successfully!
                            
                            **Order ID:** #{paid_order.id}  
                            **Total:** {paid_order.total:,} ₸  
                            **Status:** Paid
                            """
                        )
                        
                        st.sidebar.info("🎫 Your tickets are now available!")
                        
                        # Очищаем корзину
                        st.session_state.cart = []
                        st.rerun()

                elif hasattr(result, "error"):
                    error_data = result.error
                    error_message = error_data.get('error', 'Unknown error occurred')
                    
                    st.sidebar.error(f"❌ Order Failed: {error_message}")
                    
                    # ✅ ГЕНЕРИРУЕМ ГЛОБАЛЬНОЕ СОБЫТИЕ CANCELLED при ошибке
                    event_bus.publish("CANCELLED", {
                        "reason": "order_processing_failed",
                        "error_type": error_data.get('type', 'validation_error'),
                        "error_message": error_message,
                        "total_amount": total,
                        "user_id": st.session_state.user.id,
                        "timestamp": datetime.now().isoformat()
                    })

    else:
        # Пустая корзина
        st.sidebar.markdown(
            """
            <div style="text-align: center; padding: 20px; color: #666;">
                <div style="font-size: 3em;">🛒</div>
                <div style="font-size: 1.2em; font-weight: bold;">Your cart is empty</div>
                <div>Add some tickets to get started!</div>
            </div>
            """, 
            unsafe_allow_html=True
        )
        
        # Кнопка для быстрого поиска событий
        if st.sidebar.button("🔍 Find Events", use_container_width=True):
            # Публикуем событие поиска
            event_bus.publish("SEARCH", {
                "user_id": st.session_state.user.id if st.session_state.user else "anonymous",
                "search_context": "empty_cart_navigation",
                "timestamp": datetime.now().isoformat()
            })
            # Переключаем на страницу событий (если у вас есть навигация)
            st.sidebar.info("Navigate to Events page to browse available tickets!")

# Страницы
def overview_page():
    st.markdown('<div class="main-header">🎭 Event Management System</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-header">📊 System Overview</div>', unsafe_allow_html=True)

    overview_col1, overview_col2, overview_col3, overview_col4 = st.columns(4)

    with overview_col1:
        st.markdown(f"""
        <div class="metric-card">
            <h3>🏛 Venues</h3>
            <p>Currently <b>{len(st.session_state.venues)} venues</b> available for events!</p>
        </div>
        """, unsafe_allow_html=True)

    with overview_col2:
        st.markdown(f"""
        <div class="metric-card">
            <h3>🎪 Events</h3>
            <p>Currently hosting <b>{len(st.session_state.events)} active events</b>: concerts, shows, and more!</p>
        </div>
        """, unsafe_allow_html=True)

    with overview_col3:
        st.markdown(f"""
        <div class="metric-card">
            <h3>🎫 Ticket Types</h3>
            <p>We have <b>{len(st.session_state.ticket_types)} types of tickets</b> for all events.</p>
        </div>
        """, unsafe_allow_html=True)

    with overview_col4:
        avg_price = average_price(st.session_state.prices)
        st.markdown(f"""
        <div class="metric-card">
            <h3>💰 Avg Price</h3>
            <p>The average ticket price is <b>{avg_price:,.0f} ₸</b>.</p>
        </div>
        """, unsafe_allow_html=True)
    
def events_page():
    st.markdown('<div class="section-header">🎪 All Events</div>', unsafe_allow_html=True)
    
    for event in st.session_state.events:
        venue = next((v for v in st.session_state.venues 
                     if v.id == next((h.venue_id for h in st.session_state.halls if h.id == event.hall_id), None)), None)
        
        st.markdown(f"""
        <div class="event-card">
            <h3>🎭 {event.title}</h3>
            <p>📅 <strong>Date:</strong> {event.start} to {event.end}</p>
            <p>🏟 <strong>Venue:</strong> {venue.name if venue else 'Unknown'} | 📍 {venue.city if venue else 'Unknown'}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Добавляем кнопки для добавления в корзину
        event_tickets = [t for t in st.session_state.ticket_types if t.event_id == event.id]
        if event_tickets and st.session_state.user:
            st.write("Available tickets:")
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
                        
                        # ✅ ГЕНЕРИРУЕМ СОБЫТИЕ SEARCH при добавлении в корзину
                        if 'frp_data' in st.session_state:
                            st.session_state.frp_data["events_history"].append("SEARCH")
                            st.session_state.frp_data["total_searches"] = st.session_state.frp_data.get("total_searches", 0) + 1
                        
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
            if st.button("🛒 Add to cart", key=f"add_{ticket.id}"):
                cart_item = CartItem(
                    id=f"cart_{len(st.session_state.cart)}_{ticket.id}",
                    ticket_type_id=ticket.id,
                    qty=1
                )
                st.session_state.cart.append(cart_item)
                
                # ✅ ГЕНЕРИРУЕМ СОБЫТИЕ SEARCH при добавлении в корзину
                if 'frp_data' in st.session_state:
                    st.session_state.frp_data["events_history"].append("SEARCH")
                    st.session_state.frp_data["total_searches"] = st.session_state.frp_data.get("total_searches", 0) + 1
                
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
                        <strong>🏛 {venue.name}</strong><br>
                        📍 {venue.city} | 🆔 {venue.id}
</div>
                    """, unsafe_allow_html=True)
                with venue_col2:
                    if st.button("🗑 Delete", key=f"admin_del_venue_{i}"):
                        st.session_state.venues.pop(i)
                        st.rerun()

def advanced_search_page():
    st.markdown('<div class="section-header">🎯 Advanced Search</div>', unsafe_allow_html=True)
    st.write("Find exactly what you're looking for with our smart filters!")
    
    # Импортируем глобальную шину событий
    from core.frp import event_bus
    from datetime import datetime
    
    # Фильтры в колонках
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📍 Location & Date")
        selected_city = st.selectbox("City", ["All Cities"] + list(set(v.city for v in st.session_state.venues)))
        start_date = st.text_input("From Date", "2025-01-01")
        end_date = st.text_input("To Date", "2025-12-31")
    
    with col2:
        st.subheader("💰 Budget & Preferences")
        min_price, max_price = st.slider("Price Range (₸)", 0, 50000, (0, 20000), 1000)
        show_refundable = st.checkbox("Show only refundable tickets", value=False)
    
    # Кнопка поиска
    if st.button("🔍 Search with Smart Filters", type="primary"):
        
        # ✅ ГЕНЕРИРУЕМ ГЛОБАЛЬНОЕ СОБЫТИЕ SEARCH при поиске
        event_bus.publish("SEARCH", {
            "search_type": "advanced_search",
            "city": selected_city,
            "date_range": f"{start_date} to {end_date}",
            "price_range": f"{min_price}-{max_price}",
            "refundable_only": show_refundable,
            "user_id": st.session_state.user.id if st.session_state.user else "anonymous",
            "timestamp": datetime.now().isoformat()
        })
        
        # ПРИМЕНЯЕМ ФИЛЬТРЫ С ЛЯМБДАМИ
        filtered_events = list(st.session_state.events)
        
        if selected_city != "All Cities":
            # ИСПОЛЬЗУЕМ ЗАМЫКАНИЕ С ЛЯМБДАМИ
            city_filter = by_city(selected_city)
            filtered_events = city_filter(
                tuple(st.session_state.events), 
                tuple(st.session_state.venues), 
                tuple(st.session_state.halls)
            )
        
        # Фильтр по дате
        date_filter = by_date_range(start_date, end_date)
        filtered_events = date_filter(tuple(filtered_events))
        
        # Фильтр по цене
        event_ids = [e.id for e in filtered_events]
        event_tickets = [t for t in st.session_state.ticket_types if t.event_id in event_ids]
        price_filter = by_price_range(min_price, max_price)
        filtered_tickets = price_filter(tuple(event_tickets), tuple(st.session_state.prices))
        
        # Дополнительные фильтры
        if show_refundable:
            filtered_tickets = [t for t in filtered_tickets if t.refundable]
        
        # Сохраняем результаты для отображения
        st.session_state.filtered_tickets = filtered_tickets
        st.session_state.filtered_events = filtered_events
        
        # Результаты
        if filtered_tickets:
            st.success(f"🎉 Found {len(filtered_tickets)} matching tickets!")
            
            for ticket in filtered_tickets:
                event = next((e for e in filtered_events if e.id == ticket.event_id), None)
                venue = next((v for v in st.session_state.venues 
                            if v.id == next((h.venue_id for h in st.session_state.halls 
                                           if h.id == event.hall_id), None)), None) if event else None
                price = get_ticket_price(ticket.id, st.session_state.prices)
                zone = next((z for z in st.session_state.zones if z.id == ticket.zone_id), None)
                
                # Показываем структуру зала с помощью РЕКУРСИИ
                if venue and zone:
                    venue_halls = [h for h in st.session_state.halls if h.venue_id == venue.id]
                    for hall in venue_halls:
                        hall_zones = [z for z in st.session_state.zones if z.hall_id == hall.id]
                        
                        # РЕКУРСИЯ: получаем иерархию зон
                        zone_hierarchy = get_zone_hierarchy(tuple(hall_zones), zone.id)
                        
                        if zone_hierarchy:
                            with st.expander(f"🏟 {ticket.title} - Seating Details"):
                                st.write(f"Venue: {venue.name}, {venue.city}")
                                st.write(f"Zone: {zone.name}")
                                
                                # РЕКУРСИЯ: показываем путь к зоне
                                st.write("Location in venue:")
                                for z, level in zone_hierarchy:
                                    indent = "&nbsp;" * (level * 4)
                                    st.markdown(f"{indent}📌 {z.name}", unsafe_allow_html=True)
                
                # Информация о билете
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"{ticket.title}")
                    st.write(f"🎭 {event.title if event else ''} | 📍 {venue.city if venue else ''}")
                    st.write(f"💰 {price:,} ₸ | 🔄 {'Refundable' if ticket.refundable else 'Non-refundable'}")
                
                with col2:
                    if st.session_state.user:
                        if st.button("🛒 Add to Cart", key=f"adv_{ticket.id}"):
                            cart_item = CartItem(
                                id=f"cart_{len(st.session_state.cart)}_{ticket.id}",
                                ticket_type_id=ticket.id,
                                qty=1
                            )
                            st.session_state.cart.append(cart_item)
                            
                            # ✅ ГЕНЕРИРУЕМ ГЛОБАЛЬНОЕ СОБЫТИЕ SEARCH при добавлении в корзину
                            event_bus.publish("SEARCH", {
                                "search_type": "add_to_cart_from_search",
                                "ticket_type_id": ticket.id,
                                "ticket_title": ticket.title,
                                "price": price,
                                "user_id": st.session_state.user.id if st.session_state.user else "anonymous",
                                "timestamp": datetime.now().isoformat()
                            })
                            
                            st.success("Added to cart!")
                            st.rerun()
                    else:
                        st.info("Login to buy")
                
                st.markdown("---")
        else:
            st.warning("😔 No tickets found matching your criteria")


def venue_details_page():
    st.markdown('<div class="section-header">🏟 Venue Details</div>', unsafe_allow_html=True)
    
    # Выбор площадки
    selected_venue = st.selectbox(
        "Select Venue", 
        st.session_state.venues,
        format_func=lambda v: f"{v.name} - {v.city}"
    )
    
    if selected_venue:
        # Информация о площадке
        st.markdown(f"""
        <div class="venue-card">
            <h3>🏛 {selected_venue.name}</h3>
            <p>📍 <strong>City:</strong> {selected_venue.city}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Залы этой площадки
        venue_halls = [h for h in st.session_state.halls if h.venue_id == selected_venue.id]
        
        if venue_halls:
            st.subheader("🎪 Halls at this Venue")
            
            for hall in venue_halls:
                # События в этом зале
                hall_events = [e for e in st.session_state.events if e.hall_id == hall.id]
                
                st.markdown(f"""
                <div class="hall-card">
                    <h4>🏟 {hall.name}</h4>
                    <p>Capacity: <strong>{hall.capacity} people</strong></p>
                    <p>Upcoming events: <strong>{len(hall_events)}</strong></p>
                </div>
                """, unsafe_allow_html=True)
                
                # РЕКУРСИЯ: показываем структуру зон зала
                hall_zones = [z for z in st.session_state.zones if z.hall_id == hall.id]
                if hall_zones:
                    with st.expander(f"📋 Zone Structure for {hall.name}"):
                        # РЕКУРСИЯ: получаем плоский список зон в правильном порядке
                        flattened_zones = flatten_zone_tree(tuple(hall_zones))
                        
                        st.write("**Zone Hierarchy:**")
                        for zone in flattened_zones:
                            # Определяем уровень вложенности
                            level = 0
                            current_zone = zone
                            while current_zone.parent_id:
                                level += 1
                                current_zone = next((z for z in hall_zones if z.id == current_zone.parent_id), None)
                                if not current_zone:
                                    break
                            
                            indent = "&nbsp;" * (level * 4)
                            seats_info = f" ({zone.seats} seats)" if zone.seats else " (Standing zone)"
                            st.markdown(f"{indent}📍 {zone.name}{seats_info}", unsafe_allow_html=True)
                
                # Предстоящие события
                if hall_events:
                    st.write("**Upcoming Events:**")
                    for event in hall_events:
                        event_tickets = [t for t in st.session_state.ticket_types if t.event_id == event.id]
                        
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.write(f"🎭 {event.title}")
                            st.write(f"📅 {event.start} to {event.end}")
                            st.write(f"🎫 {len(event_tickets)} ticket types available")
                        
                        with col2:
                            if st.session_state.user and event_tickets:
                                if st.button("View Tickets", key=f"venue_{event.id}"):
                                    # Переходим к событиям и автоматически фильтруем по этому событию
                                    st.session_state.selected_event = event.id
                                    # Здесь можно добавить навигацию если нужно
                                    st.info(f"Check '{event.title}' in Events page!")
                
                st.markdown("---")
        else:
            st.info("No halls available for this venue")
def venue_details_page():
    st.markdown('<div class="section-header">🏟️ Venue Details</div>', unsafe_allow_html=True)
    
    if not st.session_state.venues:
        st.info("No venues available")
        return
    
    # Выбор площадки
    venue_options = [f"{v.name} ({v.city})" for v in st.session_state.venues]
    selected_venue = st.selectbox("Select Venue", venue_options)
    
    if selected_venue:
        venue_name = selected_venue.split(" (")[0]
        venue = next((v for v in st.session_state.venues if v.name == venue_name), None)
        
        if venue:
            st.header(venue.name)
            st.write(f"📍 {venue.city}")
            
            # Находим залы этой площадки
            venue_halls = [h for h in st.session_state.halls if h.venue_id == venue.id]
            
            for hall in venue_halls:
                st.subheader(f"🎪 {hall.name}")
                st.write(f"Capacity: {hall.capacity} people")
                
                # ИСПОЛЬЗУЕМ РЕКУРСИЮ - получаем зоны этого зала
                hall_zones = [z for z in st.session_state.zones if z.hall_id == hall.id]
                
                if hall_zones:
                    # Находим корневые зоны (без parent_id)
                    root_zones = [z for z in hall_zones if z.parent_id is None]
                    
                    for root_zone in root_zones:
                        with st.expander(f"📋 {root_zone.name} - Seating Structure"):
                            # РЕКУРСИЯ: получаем иерархию зон
                            zone_hierarchy = get_zone_hierarchy(tuple(hall_zones), root_zone.id)
                            
                            # РЕКУРСИЯ: подсчитываем общее количество мест
                            total_seats = calculate_total_seats(tuple(hall_zones), root_zone.id)
                            
                            st.write(f"**Total seats:** {total_seats}")
                            st.write("**Zone hierarchy:**")
                            
                            for zone, level in zone_hierarchy:
                                indent = "&nbsp;" * (level * 4)
                                seats_info = f" - {zone.seats} seats" if zone.seats else " - Standing area"
                                st.markdown(f"{indent}📌 {zone.name}{seats_info}", unsafe_allow_html=True)
                
                st.markdown("---")
def reports_page():
    st.markdown('<div class="section-header">📊 Reports & Analytics</div>', unsafe_allow_html=True)
    
    if not st.session_state.user or not is_admin(st.session_state.user):
        st.error("🚫 Admin access required")
        return
    
    # Добавляем вкладки для разных отчетов
    tab1, tab2, tab3 = st.tabs(["⚡️ Cache Performance", "🚀 Lazy Computations", "📈 Sales Reports"])
    
    with tab1:
        st.markdown("### 🎯 Memoization")
        st.write("Quotes (cached) - testing memoization performance")
        
        # Кнопка теста производительности кэша
        if st.button("🚀 Run Cache Performance Test", type="primary", key="cache_test"):
            with st.spinner("Running performance test..."):
                time_no_cache, time_with_cache = benchmark_quotes(300)
            
            # Показываем результаты
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Time without cache", f"{time_no_cache:.0f} ms")
            with col2:
                st.metric("Time with cache", f"{time_with_cache:.0f} ms")
            with col3:
                speedup = time_no_cache / time_with_cache if time_with_cache > 0 else 0
                st.metric("Speed Improvement", f"{speedup:.1f}x")
            
            # График
            st.write("Performance comparison:")
            chart_data = {
                'Scenario': ['Without Cache', 'With Cache'],
                'Time (ms)': [time_no_cache, time_with_cache]
            }
            st.bar_chart(chart_data, x='Scenario', y='Time (ms)')
            
            # Информация о кэше
            cache_info = quote_tickets.cache_info()
            st.write("Cache Statistics:")
            st.write(f"- Hits: {cache_info.hits} ")
            st.write(f"- Misses: {cache_info.misses} ")
            st.write(f"- Cache Size: {cache_info.currsize}/{cache_info.maxsize} ")
    
    with tab2:
        st.markdown("### 🚀 Lazy computations")
        
        # Демонстрация ленивого потока заказов
        st.markdown("#### 🛒 Lazy Order filtering")
        status_filter = st.selectbox("Order status", ["all", "paid", "held", "cancelled"], key="lazy_filter")
        
        if status_filter != "all":
            from core.lazy import iter_orders
            filtered_orders = list(iter_orders(tuple(st.session_state.orders), lambda o: o.status == status_filter))
            st.write(f"🎯 Найдено заказов: **{len(filtered_orders)}**")
            
            # Показываем несколько заказов
            st.write("First 5 orders:")
            for order in filtered_orders[:5]:
                st.write(f"- Order #{order.id}: {order.status} - {order.total:,} ₸")
        
        # Демонстрация онлайн-потока сканирований
        st.markdown("#### 📊 Real-time Gate Load")
        window_size = st.slider("Analysis window (minutes)", 1, 30, 5, key="lazy_window")
        
        if st.button("Start stream", key="lazy_demo"):
            from core.lazy import lazy_gate_flow, simulate_scan_stream
            
            # Симуляция потока сканирований
            with st.spinner("Generating scan stream..."):
                simulated_scans = simulate_scan_stream(100)
                flow_data = list(lazy_gate_flow(simulated_scans, window_size))
            
            # Визуализация
            if flow_data:
                st.success(f"✅ Generated {len(flow_data)} measurements!")
                
                # Берем последние уникальные состояния для красивого графика
                latest_counts = {}
                for gate_id, count in flow_data[-20:]:  # Последние 20 измерений
                    latest_counts[gate_id] = count
                
                if latest_counts:
                    st.bar_chart(latest_counts)
                    
                    # Показываем сырые данные
                    with st.expander("📋 Show the raw data"):
                        st.write("Last 10 measurements:")
                        for gate_id, count in list(flow_data[-10:]):
                            st.write(f"- {gate_id}: {count} customer(s)")
                else:
                    st.info("ℹ️ No data to display")
    
    with tab3:
        st.markdown("### 📈 Sales Analytics Dashboard")
        # Твоя существующая логика отчетов по продажам
        st.info("General sales reports and analytics")
        
        # Live statistics - ПО ВСЕМ заказам (полная картина)
    # Initialize new orders list if not exists
    if 'new_orders' not in st.session_state:
        st.session_state.new_orders = []
    
    # ALL STATISTICS - both overall and new orders
    total_orders = len(st.session_state.orders)
    paid_orders = len([o for o in st.session_state.orders if o.status == "paid"])
    total_revenue = sum([o.total for o in st.session_state.orders if o.status == "paid"])
    
    new_orders = st.session_state.new_orders
    total_new_orders = len(new_orders)
    paid_new_orders = len([o for o in new_orders if o.status == "paid"])
    total_new_revenue = sum(o.total for o in new_orders if o.status == "paid")
    
    # Overall Statistics
    st.markdown("#### 📊 Overall Statistics")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Orders", total_orders)
    with col2:
        st.metric("Paid Orders", paid_orders)
    with col3:
        st.metric("Total Revenue", f"{total_revenue:,} ₸")
    
    # New Orders Statistics (Live)
    st.markdown("#### 🆕 Live Session Statistics")
    col4, col5, col6 = st.columns(3)
    with col4:
        st.metric("New Orders", total_new_orders)
    with col5:
        st.metric("Paid New Orders", paid_new_orders)
    with col6:
        st.metric("New Revenue", f"{total_new_revenue:,} ₸")
    
    # Recent Orders Feed - only new orders from current session
    st.markdown("#### 📋 Recent Orders (Current Session)")
    
    if new_orders:
        # Show in reverse order (newest first)
        for order in reversed(new_orders[-10:]):  # last 10 new orders
            status_icon = "✅" if order.status == "paid" else "⏳"
            timestamp = "Just now"
            st.write(f"{status_icon} Order #{order.id} - {order.total:,} ₸ - {order.status} - {timestamp}")
    else:
        st.info("📭 No new orders yet. Orders will appear here as users make purchases.")
    
    # Clear history button (optional)
    if new_orders and st.button("🔄 Clear Session History", key="clear_orders"):
        st.session_state.new_orders = []
        st.rerun()
   
def functional_core_page():
    st.markdown('<div class="section-header">⚡️ Functional Core - Smart Error Handling</div>', unsafe_allow_html=True)
    
    st.write("**Testing Maybe/Either patterns for safe operations**")
    
    # Раздели на колонки
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🎫 Test Maybe Monad", use_container_width=True):
            test_maybe_demo()
    
    with col2:
        if st.button("🛒 Test Either Monad", use_container_width=True):
            test_either_demo()
    
    with col3:
        if st.button("📦 Test Full Pipeline", use_container_width=True):
            test_pipeline_demo()
    
    # Покажем текущую корзину если есть
    if st.session_state.cart:
        st.markdown("---")
        st.write("**Current cart items for testing:**")
        for item in st.session_state.cart:
            st.write(f"- {get_ticket_display_name_safe(item.ticket_type_id)} (Qty: {item.qty})")

def test_maybe_demo():
    """Демо Maybe монады"""
    from core.transforms import safe_ticket
    
    st.markdown("### 🎫 Maybe Demo - Safe Ticket Search")
    
    # Тестовые данные
    test_ticket_id = "t1"  # Можно сделать selectbox для выбора
    
    result = safe_ticket(tuple(st.session_state.ticket_types), test_ticket_id)
    
    ticket = result.get_or_else(None)
    
    if ticket:
        st.success(f"✅ **Ticket Found!**")
        st.write(f"**Name:** {ticket.title}")
        st.write(f"**Event ID:** {ticket.event_id}")
        st.write(f"**Refundable:** {'Yes' if ticket.refundable else 'No'}")
    else:
        st.error(f"❌ **Ticket Not Found**")
        st.write(f"Ticket ID '{test_ticket_id}' doesn't exist")

def test_either_demo():
    """Демо Either монады"""
    from core.transforms import validate_cart_item
    
    st.markdown("### 🛒 Either Demo - Cart Validation")
    
    if not st.session_state.cart:
        st.warning("🛒 Your cart is empty! Add some tickets first.")
        return
    
    # Берем первый item из корзины
    test_item = st.session_state.cart[0]
    
    st.write(f"**Testing item:** {get_ticket_display_name_safe(test_item.ticket_type_id)}")
    st.write(f"**Quantity:** {test_item.qty}")
    
    result = validate_cart_item(
        test_item, 
        tuple(st.session_state.quotas),
        tuple(st.session_state.rules)
    )
    
    # Проверяем тип результата
    if hasattr(result, 'value'):  # Right case
        st.success("✅ **Validation PASSED!**")
        st.write("Item is valid and can be purchased")
        
        # Покажем информацию о квотах
        quota = next((q for q in st.session_state.quotas if q.ticket_type_id == test_item.ticket_type_id), None)
        if quota:
            st.info(f"📊 Quota info: {quota.sold}/{quota.total} sold, {quota.total - quota.sold} available")
    
    elif hasattr(result, 'error'):  # Left case
        st.error("❌ **Validation FAILED!**")
        error_data = result.error
        st.write(f"**Error:** {error_data.get('error', 'Unknown error')}")
        
        if 'available' in error_data:
            st.write(f"**Available:** {error_data['available']}")
        if 'requested' in error_data:
            st.write(f"**Requested:** {error_data['requested']}")

def test_pipeline_demo():
    """Демо полного пайплайна (автоматический запуск без кнопок)"""
    from core.compose import create_order_pipeline

    st.markdown("### 📦 Full Order Pipeline Demo")
    st.divider()

    if not st.session_state.cart:
        st.warning("🛒 Your cart is empty! Add some tickets first.")
        return

    with st.spinner("Running order pipeline..."):
        result = create_order_pipeline(
            tuple(st.session_state.cart),
            tuple(st.session_state.ticket_types),
            tuple(st.session_state.quotas),
            tuple(st.session_state.rules),
            tuple(st.session_state.prices)
        )

    st.markdown("#### Pipeline Results:")

    # --- Успешный результат ---
    if hasattr(result, "value"):
        order = result.value
        st.success("✅ Order Created Successfully!")
        st.write(f"Order ID: {order.id}")
        st.write(f"Total Amount: {order.total:,} ₸")
        st.write(f"Status: {order.status}")

    # --- Ошибка ---
    elif hasattr(result, "error"):
        error_data = result.error
        st.error("❌ Pipeline Failed!")
        st.write(f"Error: {error_data.get('error', 'Unknown error')}")
        
# Не забудь добавить эту функцию если её нет
def get_ticket_display_name_safe(ticket_type_id):
    """Безопасное получение названия билета"""
    try:
        ticket_type = next((t for t in st.session_state.ticket_types if t.id == ticket_type_id), None)
        if not ticket_type:
            return f"Ticket {ticket_type_id}"
        
        event = next((e for e in st.session_state.events if e.id == ticket_type.event_id), None)
        event_name = event.title if event else "Unknown Event"
        
        return f"{ticket_type.title} - {event_name}"
    except:
        return f"Ticket {ticket_type_id}"
def frp_page():
    st.markdown("### 🚀 FRP - Real-time Event Processing (Global Event Bus)")
    
    # Используем глобальный EventBus вместо session_state
    from core.frp import event_bus
    
    # Автоматическое обновление каждые 3 секунды
    import time
    if 'last_frp_update' not in st.session_state:
        st.session_state.last_frp_update = time.time()
    
    if time.time() - st.session_state.last_frp_update > 3:
        st.session_state.last_frp_update = time.time()
        st.rerun()
    
    # Получаем текущее состояние из глобальной шины
    current_state = event_bus.get_current_state()
    stats = current_state["stats"]
    events_history = current_state["events"]
    
    # Информация о подключении
    st.info("🌐 **Connected to Global Event Bus** - Events will appear on all connected devices/browsers")
    
    # Кнопка для ручного обновления
    col_refresh, col_stats, col_time = st.columns([1, 2, 2])
    with col_refresh:
        if st.button("🔄 Refresh Now"):
            st.rerun()
    with col_stats:
        st.caption(f"📊 Total events in system: {len(events_history)}")
    with col_time:
        st.caption(f"🕐 Last update: {datetime.now().strftime('%H:%M:%S')}")
    
    # Основные метрики из ГЛОБАЛЬНОГО состояния
    st.markdown("#### 📊 Live System Metrics")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        searches_count = len([e for e in events_history if e.name == "SEARCH"])
        st.metric("Searches", searches_count, delta=None)
    
    with col2:
        holds_count = len([e for e in events_history if e.name == "HOLD"])
        st.metric("Total Holds", holds_count)
        st.metric("Active Holds", stats["active_holds"])
    
    with col3:
        purchases_count = stats["total_purchases"]
        st.metric("Purchases", purchases_count)
        st.metric("Revenue", f"{stats['total_revenue']:,} ₸")
    
    with col4:
        scans_count = stats["total_scans"]
        # ✅ ИСПРАВЛЕННЫЙ Success Rate - проверяем деление на ноль
        success_rate = (stats["successful_scans"] / max(scans_count, 1)) * 100
        st.metric("Total Scans", scans_count)
        st.metric("Success Rate", f"{success_rate:.1f}%")
    
    # Cancellations отдельно
    cancellations_count = len([e for e in events_history if e.name == "CANCELLED"])
    st.metric("Cancellations", cancellations_count)
    
    # Live events feed из ГЛОБАЛЬНОЙ истории - ИСПРАВЛЕННОЕ ВРЕМЯ
    st.markdown("#### 📋 Global Event Stream (Live)")
    
    if events_history:
        # Группируем события по типам для статистики
        event_types = {}
        for event in events_history:
            event_types[event.name] = event_types.get(event.name, 0) + 1
        
        st.caption(f"Event distribution: {', '.join([f'{k}: {v}' for k, v in event_types.items()])}")
        
        # Отображаем последние события
        recent_events = list(reversed(events_history[-20:]))  # Последние 20 событий
        
        for event in recent_events:
            # Иконки для разных типов событий
            icon_config = {
                "SEARCH": {"icon": "🔍", "color": "#4CAF50"},
                "HOLD": {"icon": "📦", "color": "#FF9800"}, 
                "PURCHASED": {"icon": "💰", "color": "#2196F3"},
                "CANCELLED": {"icon": "❌", "color": "#F44336"},
                "SCANNED": {"icon": "🎫", "color": "#9C27B0"},
                "PRICE_CHANGED": {"icon": "📊", "color": "#607D8B"}
            }
            
            config = icon_config.get(event.name, {"icon": "⚡️", "color": "#757575"})
            
            # ⚡️ ИСПРАВЛЕНИЕ: используем время события, а не текущее время
            try:
                # Парсим время из события (оно уже есть в event.ts)
                event_time = datetime.fromisoformat(event.ts)
                # Форматируем с секундами
                formatted_time = event_time.strftime('%H:%M:%S')
                # Добавляем дату, если событие не сегодняшнее
                if event_time.date() != datetime.now().date():
                    formatted_time = event_time.strftime('%m/%d %H:%M:%S')
            except:
                formatted_time = "Unknown time"
            
            # Красивое отображение события
            st.markdown(
                f"""
                <div style="border-left: 4px solid {config['color']}; padding: 8px 12px; margin: 4px 0; background: #f8f9fa; border-radius: 4px;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-weight: bold; color: {config['color']};">
                            {config['icon']} {event.name}
                        </span>
                        <span style="color: #666; font-size: 0.9em; font-family: monospace;">{formatted_time}</span>
                    </div>
                </div>
                """, 
                unsafe_allow_html=True
            )
            
            # Дополнительная информация о событии
            if event.payload:
                with st.expander("Event Details", expanded=False):
                    st.json(event.payload)
                    
                    # Показываем сколько времени прошло с момента события
                    try:
                        event_time = datetime.fromisoformat(event.ts)
                        time_diff = datetime.now() - event_time
                        minutes_ago = int(time_diff.total_seconds() / 60)
                        seconds_ago = int(time_diff.total_seconds())
                        
                        if minutes_ago == 0:
                            time_text = f"{seconds_ago} seconds ago"
                        elif minutes_ago < 60:
                            time_text = f"{minutes_ago} minutes ago"
                        else:
                            hours_ago = minutes_ago // 60
                            time_text = f"{hours_ago} hours ago"
                            
                        st.caption(f"🕐 Event occurred: {time_text}")
                    except:
                        pass
    else:
        st.info("🚀 No events yet. Use the test buttons below or make purchases to see live events!")
    
    # Расширенные аналитические панели с правильным временем
    st.markdown("#### 📈 Analytics Dashboards")
    
    tab1, tab2, tab3 = st.tabs(["💰 Sales Analytics", "🎫 Gate Analytics", "📊 Event Timeline"])
    
    with tab1:
        # Аналитика продаж по часам
        purchases = [e for e in events_history if e.name == "PURCHASED"]
        if purchases:
            hourly_sales = {}
            for purchase in purchases:
                try:
                    hour = datetime.fromisoformat(purchase.ts).strftime("%H:00")
                    amount = purchase.payload.get("amount", purchase.payload.get("total_amount", 0))
                    hourly_sales[hour] = hourly_sales.get(hour, 0) + amount
                except:
                    continue
            
            if hourly_sales:
                st.markdown("**Sales by Hour**")
                max_sales = max(hourly_sales.values()) if hourly_sales else 1
                for hour, amount in sorted(hourly_sales.items()):
                    progress = min(amount / max_sales, 1.0)
                    st.progress(progress, text=f"{hour}: {amount:,} ₸")
        else:
            st.info("No purchase data available")
    
    with tab2:
        # Статистика по воротам
        scans = [e for e in events_history if e.name == "SCANNED"]
        if scans:
            gate_stats = {}
            for scan in scans[-50:]:  # Последние 50 сканирований
                gate_id = scan.payload.get("gate_id", "unknown")
                if gate_id not in gate_stats:
                    gate_stats[gate_id] = {"total": 0, "successful": 0}
                
                gate_stats[gate_id]["total"] += 1
                if scan.payload.get("ok", False):
                    gate_stats[gate_id]["successful"] += 1
            
            if gate_stats:
                st.markdown("**Gate Performance (Last 50 scans)**")
                for gate_id, stats_data in gate_stats.items():
                    rate = (stats_data["successful"] / max(stats_data["total"], 1)) * 100
                    st.write(f"**Gate `{gate_id}`**: {stats_data['successful']}/{stats_data['total']} ({rate:.1f}%)")
        else:
            st.info("No scan data available")
    
    with tab3:
        # Временная шкала событий
        if events_history:
            st.markdown("**Recent Event Timeline**")
            
            # Берем последние 10 событий
            recent_for_timeline = events_history[-10:]
            
            for event in reversed(recent_for_timeline):
                try:
                    event_time = datetime.fromisoformat(event.ts)
                    time_str = event_time.strftime('%H:%M:%S')
                    
                    icon_config = {
                        "SEARCH": "🔍", "HOLD": "📦", "PURCHASED": "💰", 
                        "CANCELLED": "❌", "SCANNED": "🎫", "PRICE_CHANGED": "📊"
                    }
                    
                    icon = icon_config.get(event.name, "⚡️")
                    
                    # Показываем как давно было событие
                    time_diff = datetime.now() - event_time
                    seconds_ago = int(time_diff.total_seconds())
                    
                    if seconds_ago < 60:
                        ago_text = f"{seconds_ago}s ago"
                    else:
                        ago_text = f"{seconds_ago//60}m ago"
                    
                    st.write(f"{icon} `{time_str}` - **{event.name}** (*{ago_text}*)")
                    
                except:
                    st.write(f"⚡️ {event.name} - Time unknown")
        else:
            st.info("No events for timeline")
    
    # Кнопки для тестирования - публикуют в ГЛОБАЛЬНУЮ шину
    st.markdown("#### 🎮 Test Global Events")
    st.warning("These events will appear on ALL connected devices/browsers with correct timestamps!")
    
    test_col1, test_col2, test_col3, test_col4 = st.columns(4)
    
    with test_col1:
        if st.button("🔍 Global Search", use_container_width=True):
            event_bus.publish("SEARCH", {
                "event_id": f"event_{int(time.time())}",
                "user_query": "concert tickets",
                "results_count": 8,
                "timestamp": datetime.now().isoformat()  # ✅ Правильное время
            })
            st.rerun()
    
    with test_col2:
        if st.button("📦 Global Hold", use_container_width=True):
            event_bus.publish("HOLD", {
                "order_id": f"hold_{int(time.time())}",
                "items": [{"ticket_type": "VIP", "qty": 2}, {"ticket_type": "STANDARD", "qty": 1}],
                "amount": 15000,
                "user_id": "test_user",
                "timestamp": datetime.now().isoformat()  # ✅ Правильное время
            })
            st.rerun()
    
    with test_col3:
        if st.button("💰 Global Purchase", use_container_width=True):
            event_bus.publish("PURCHASED", {
                "order_id": f"order_{int(time.time())}",
                "items": [{"ticket_type": "VIP", "qty": 2}],
                "amount": 20000,
                "currency": "KZT",
                "user_id": "test_user",
                "timestamp": datetime.now().isoformat()  # ✅ Правильное время
            })
            st.rerun()
    
    with test_col4:
        if st.button("🎫 Global Scan", use_container_width=True):
            event_bus.publish("SCANNED", {
                "order_id": f"order_scan_{int(time.time())}",
                "gate_id": f"gate_{int(time.time()) % 3 + 1}",
                "ok": True,
                "timestamp": datetime.now().isoformat()  # ✅ Правильное время
            })
            st.rerun()
    
    # Дополнительные тестовые события
    test_col5, test_col6 = st.columns(2)
    
    with test_col5:
        if st.button("❌ Global Cancel", use_container_width=True):
            event_bus.publish("CANCELLED", {
                "order_id": f"cancel_{int(time.time())}",
                "reason": "test_cancellation",
                "user_id": "test_user",
                "timestamp": datetime.now().isoformat()  # ✅ Правильное время
            })
            st.rerun()
    
    with test_col6:
        if st.button("📊 Price Change", use_container_width=True):
            event_bus.publish("PRICE_CHANGED", {
                "ticket_type_id": f"type_{int(time.time()) % 10}",
                "old_price": 5000,
                "new_price": 4500,
                "reason": "dynamic_pricing",
                "timestamp": datetime.now().isoformat()  # ✅ Правильное время
            })
            st.rerun()

    # Информация о системе
    with st.expander("ℹ️ System Information"):
        st.write(f"**Event Bus Subscribers:**")
        for event_name, handlers in event_bus._subscribers.items():
            st.write(f"- {event_name}: {len(handlers)} handlers")
        
        st.write(f"**Last event:** {events_history[-1].name if events_history else 'None'}")
        st.write(f"**Current time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# Основное приложение
st.sidebar.markdown("# 🎭 Event System")
login_section()
cart_section()

st.sidebar.markdown("---")
st.sidebar.markdown("## 🧭 Navigation")

pages = ["🏠 Overview", "🎪 Events", "🎫 Tickets", "🎯 Advanced Search", "🏟 Venue Details"]

# Только админ видит Admin, Reports и Functional Core
if st.session_state.user and is_admin(st.session_state.user):
    pages.append("👨‍💼 Admin")
    pages.append("📊 Reports")
    pages.append("⚡️ Functional Core")
    pages.append("🔄 FRP")  # ← ДОБАВЬ ЭТУ СТРОЧКУ!

page = st.sidebar.radio("Go to:", pages, key="nav_radio")

# Обработка страниц
if "🏠" in page:
    overview_page()
elif "🎪" in page:
    events_page()
elif "🎫" in page:
    tickets_page()
elif "🎯" in page:
    advanced_search_page()
elif "🏟" in page:
    venue_details_page()
elif "📊" in page: 
    reports_page()
elif "👨‍💼" in page:
    admin_page()
elif "⚡️" in page:  
    functional_core_page()
elif "🔄" in page:
    frp_page()