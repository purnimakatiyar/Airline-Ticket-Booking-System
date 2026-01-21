"""
Management command to seed the database with sample data
Usage: python manage.py seed_data
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from bookings.models import Flight, Seat


class Command(BaseCommand):
    help = 'Seeds the database with sample flights and seats'

    def handle(self, *args, **kwargs):
        self.stdout.write('Seeding database...')

        Flight.objects.all().delete()
        Seat.objects.all().delete()

        flights_data = [
            {
                'flight_number': 'AA101',
                'origin': 'New York (JFK)',
                'destination': 'Los Angeles (LAX)',
                'departure_time': timezone.now() + timedelta(days=7),
                'arrival_time': timezone.now() + timedelta(days=7, hours=6),
                'total_seats': 180,
                'price': 299.99
            },
            {
                'flight_number': 'UA202',
                'origin': 'San Francisco (SFO)',
                'destination': 'Chicago (ORD)',
                'departure_time': timezone.now() + timedelta(days=5),
                'arrival_time': timezone.now() + timedelta(days=5, hours=4),
                'total_seats': 150,
                'price': 249.99
            },
            {
                'flight_number': 'DL303',
                'origin': 'Miami (MIA)',
                'destination': 'Seattle (SEA)',
                'departure_time': timezone.now() + timedelta(days=10),
                'arrival_time': timezone.now() + timedelta(days=10, hours=6, minutes=30),
                'total_seats': 200,
                'price': 349.99
            },
            {
                'flight_number': 'SW404',
                'origin': 'Dallas (DFW)',
                'destination': 'Boston (BOS)',
                'departure_time': timezone.now() + timedelta(days=3),
                'arrival_time': timezone.now() + timedelta(days=3, hours=4),
                'total_seats': 120,
                'price': 199.99
            },
        ]

        for flight_data in flights_data:
            flight = Flight.objects.create(**flight_data)
            self.stdout.write(f'Created flight: {flight.flight_number}')

            seat_count = 0
            
            for row in range(1, 6):
                for seat_letter in ['A', 'B', 'C', 'D']:
                    Seat.objects.create(
                        flight=flight,
                        seat_number=f'{row}{seat_letter}',
                        seat_class='BUSINESS'
                    )
                    seat_count += 1

            remaining_seats = flight.total_seats - 20
            rows_needed = (remaining_seats + 5) // 6  # 6 seats per row
            
            for row in range(6, 6 + rows_needed):
                for seat_letter in ['A', 'B', 'C', 'D', 'E', 'F']:
                    if seat_count >= flight.total_seats:
                        break
                    Seat.objects.create(
                        flight=flight,
                        seat_number=f'{row}{seat_letter}',
                        seat_class='ECONOMY'
                    )
                    seat_count += 1

            self.stdout.write(f'  Created {seat_count} seats')

        self.stdout.write(self.style.SUCCESS(f'Successfully seeded {len(flights_data)} flights with seats'))
