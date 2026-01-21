Airline Ticket Booking System

A Django-based airline booking system that manages flights, seats, bookings, payments, cancellations, and refunds. The project uses Django REST Framework for APIs and includes admin tools and optional Celery support for handling seat-hold expiration.

Features

Flight and seat management

Booking lifecycle with payment processing

Seat hold and automatic expiration

REST APIs with browsable documentation

Django admin panel

Prerequisites

Python 3.8+

pip and virtualenv

Setup Instructions
1. Create project and virtual environment
mkdir airline_booking_system
cd airline_booking_system
python -m venv venv
venv\Scripts\activate   # Windows
# or
source venv/bin/activate   # macOS/Linux

2. Install dependencies
pip install -r requirements.txt

3. Database setup (SQLite)

No manual setup required.
The default configuration in settings.py should be:

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

4. Apply migrations and create an admin user
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser

5. Seed sample data
python manage.py seed_data

6. Start the development server
python manage.py runserver


The application will be available at:
http://localhost:8000/

API Endpoints
Flights

GET /api/flights/

GET /api/flights/{id}/

GET /api/flights/{id}/available_seats/

Bookings

POST /api/bookings/

GET /api/bookings/

GET /api/bookings/{reference}/

POST /api/bookings/{reference}/initiate_payment/

POST /api/bookings/{reference}/process_payment/

POST /api/bookings/{reference}/cancel/

POST /api/bookings/{reference}/refund/

POST /api/bookings/expire_holds/

