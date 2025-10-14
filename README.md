# Event Management System

This project is a functional event management platform built in Python.  
It allows users to browse events, explore venues, buy tickets, and manage orders.  
The system demonstrates the principles of functional programming — pure functions, recursion, immutability, and higher-order functions — while keeping the structure modular and testable.

---

## Project Overview

The Event Management System provides:
- Viewing and filtering of events by city, date, or price range  
- Recursive processing of venue and zone hierarchies  
- Calculation of available seats, ticket prices, and order totals  
- Validation of user actions and ticket quotas  
- Functional-style composition of operations without side effects  
- Streamlit-based web interface for interaction  

The project uses functional data flow, ensuring safety, predictability, and code reusability.

---

## Project Structure

Event-System/
│
├── app/
│ ├── app_streamlit.py # Main Streamlit application
│ ├── style.css # UI styling
│
├── core/
│ ├── domain.py # Entity definitions (Event, Zone, TicketType, etc.)
│ ├── transforms.py # Data transformations and validation
│ ├── filters.py # Filtering functions and closures
│ ├── recursion.py # Recursive zone and seatmap logic
│ ├── memo.py # Caching and memoization
│ ├── auth.py # Authentication logic
│ ├── ftypes.py # Maybe / Either functional types
│
├── data/
│ └── seed.json # Initial dataset
│
├── tests/
│ ├── test_core.py
│ ├── test_transforms.py
│ ├── test_recursion.py
│ └── ...
│
├── requirements.txt
└── README.md

yaml

---

## Installation and Usage

### 1. Clone the repository
```bash
git clone https://github.com/zhanikoss/Event-System.git
cd Event-System
2. Set up the environment
bash

python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
3. Run the web application
bash

streamlit run app/app_streamlit.py
4. Run tests (optional)
bash

pytest -v
How to Use
Open the Streamlit application.

Browse the list of available events, venues, and ticket types.

Use filters to search by city, date, or price range.

Add tickets to your cart and confirm your order.

View total price and available quotas.

Admin users can manage venues, zones, and event data.

The interface updates dynamically and supports both user and admin modes.

Functional Programming Concepts
Pure Functions — no mutation of data

Recursion — hierarchical traversal for zones and seats

Higher-Order Functions — using map, filter, reduce, and closures

Function Composition — chaining multiple filters

Monads — Maybe and Either for safe error handling

Memoization — caching repetitive computations

Authors
Zhaniya Atabek
Aruzhan Dauletkyzy
Teya Kim



Supervisor
Kassenkhan Arai Meirambaykyzy

Technologies Used
Python 3.10+

Streamlit

Pytest

JSON data source

Functional Programming Paradigm