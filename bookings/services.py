import uuid
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from .models import Booking, Payment, Refund, Seat


class BookingService:

    @staticmethod
    def generate_booking_reference():
        """Generate unique booking reference"""
        return f"BK{uuid.uuid4().hex[:8].upper()}"

    @staticmethod
    def generate_transaction_id():
        """Generate unique transaction ID"""
        return f"TXN{uuid.uuid4().hex[:10].upper()}"

    @staticmethod
    def generate_refund_reference():
        """Generate unique refund reference"""
        return f"REF{uuid.uuid4().hex[:10].upper()}"

    @classmethod
    @transaction.atomic
    def create_booking(cls, flight, seat, passenger_name, passenger_email, passenger_phone):
        """
        Create a new booking in INITIATED state
        Uses select_for_update to lock the seat row and prevent race conditions
        """
        seat = Seat.objects.select_for_update().get(id=seat.id)
        
        if not seat.is_available():
            raise ValidationError("Seat is no longer available")

        booking = Booking.objects.create(
            booking_reference=cls.generate_booking_reference(),
            flight=flight,
            seat=seat,
            passenger_name=passenger_name,
            passenger_email=passenger_email,
            passenger_phone=passenger_phone,
            state='INITIATED',
            amount=flight.price
        )

        return booking

    @classmethod
    @transaction.atomic
    def hold_seat(cls, booking):
        """
        Transition booking from INITIATED to SEAT_HELD
        Locks the seat for 10 minutes
        """
        booking.refresh_from_db()
        
        seat = Seat.objects.select_for_update().get(id=booking.seat.id)
        if not seat.is_available():
            raise ValidationError("Seat is no longer available")

        booking.transition_to('SEAT_HELD')
        
        return booking

    @classmethod
    @transaction.atomic
    def initiate_payment(cls, booking, payment_method='MOCK'):
        """
        Transition booking from SEAT_HELD to PAYMENT_PENDING
        Create payment record
        """
        booking.refresh_from_db()
        
        if booking.is_expired():
            booking.transition_to('EXPIRED')
            raise ValidationError("Seat hold has expired")

        payment = Payment.objects.create(
            booking=booking,
            transaction_id=cls.generate_transaction_id(),
            amount=booking.amount,
            status='PENDING',
            payment_method=payment_method
        )

        booking.transition_to('PAYMENT_PENDING')
        
        return booking, payment

    @classmethod
    @transaction.atomic
    def process_payment(cls, booking, payment, simulate_failure=False):
        """
        Process payment (mocked) and transition booking to CONFIRMED or CANCELLED
        """
        booking.refresh_from_db()
        payment.refresh_from_db()

        if simulate_failure:
            payment_success = False
        else:
            payment_success = True

        # Update payment status
        payment.status = 'SUCCESS' if payment_success else 'FAILED'
        payment.processed_at = timezone.now()
        payment.save()

        if payment_success:
            booking.transition_to('CONFIRMED')
        else:
            booking.transition_to('CANCELLED')

        return booking, payment

    @classmethod
    @transaction.atomic
    def cancel_booking(cls, booking, reason=''):
        """
        Cancel a confirmed booking
        Only CONFIRMED bookings can be cancelled
        """
        booking.refresh_from_db()

        if booking.state != 'CONFIRMED':
            raise ValidationError(f"Only CONFIRMED bookings can be cancelled. Current state: {booking.state}")

        booking.transition_to('CANCELLED')
        
        return booking

    @classmethod
    @transaction.atomic
    def process_refund(cls, booking, reason=''):
        """
        Process refund for cancelled booking
        """
        booking.refresh_from_db()

        if booking.state != 'CANCELLED':
            raise ValidationError(f"Only CANCELLED bookings can be refunded. Current state: {booking.state}")

        if booking.refunds.filter(status='PROCESSED').exists():
            raise ValidationError("Booking has already been refunded")

        successful_payment = booking.payments.filter(status='SUCCESS').first()
        if not successful_payment:
            raise ValidationError("No successful payment found for this booking")

        refund = Refund.objects.create(
            booking=booking,
            payment=successful_payment,
            refund_reference=cls.generate_refund_reference(),
            amount=booking.amount,
            status='PENDING',
            reason=reason
        )

        refund.status = 'PROCESSED'
        refund.processed_at = timezone.now()
        refund.save()

        successful_payment.status = 'REFUNDED'
        successful_payment.save()

        booking.transition_to('REFUNDED')

        return booking, refund

    @classmethod
    def expire_old_seat_holds(cls):
        """
        Expire all bookings in SEAT_HELD state that have exceeded 10 minutes
        This should be called by a periodic task (Celery beat)
        """
        from django.db.models import F
        from datetime import timedelta

        now = timezone.now()
        expiry_threshold = now - timedelta(minutes=10)

        expired_bookings = Booking.objects.filter(
            state='SEAT_HELD',
            seat_held_at__lte=expiry_threshold
        )

        expired_count = 0
        for booking in expired_bookings:
            try:
                with transaction.atomic():
                    booking.refresh_from_db()
                    if booking.state == 'SEAT_HELD' and booking.is_expired():
                        booking.transition_to('EXPIRED')
                        expired_count += 1
            except Exception as e:
                print(f"Error expiring booking {booking.booking_reference}: {str(e)}")

        return expired_count


class SeatAvailabilityService:

    @staticmethod
    def get_available_seats(flight):
        """Get all available seats for a flight"""
        return Seat.objects.filter(
            flight=flight
        ).exclude(
            bookings__state__in=['SEAT_HELD', 'PAYMENT_PENDING', 'CONFIRMED']
        )

    @staticmethod
    def check_seat_availability(seat):
        """Check if a specific seat is available"""
        return seat.is_available()
