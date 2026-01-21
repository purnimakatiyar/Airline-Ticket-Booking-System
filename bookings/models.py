from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta


class Flight(models.Model):
    flight_number = models.CharField(max_length=10, unique=True)
    origin = models.CharField(max_length=100)
    destination = models.CharField(max_length=100)
    departure_time = models.DateTimeField()
    arrival_time = models.DateTimeField()
    total_seats = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'flights'
        ordering = ['-departure_time']

    def __str__(self):
        return f"{self.flight_number} - {self.origin} to {self.destination}"

    @property
    def available_seats(self):
        """Calculate available seats excluding held and confirmed bookings"""
        booked_count = self.bookings.filter(
            state__in=['SEAT_HELD', 'PAYMENT_PENDING', 'CONFIRMED']
        ).count()
        return self.total_seats - booked_count


class Seat(models.Model):
    SEAT_CLASS_CHOICES = [
        ('ECONOMY', 'Economy'),
        ('BUSINESS', 'Business'),
        ('FIRST', 'First Class'),
    ]

    flight = models.ForeignKey(Flight, on_delete=models.CASCADE, related_name='seats')
    seat_number = models.CharField(max_length=5)
    seat_class = models.CharField(max_length=10, choices=SEAT_CLASS_CHOICES, default='ECONOMY')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'seats'
        unique_together = ['flight', 'seat_number']
        ordering = ['seat_number']

    def __str__(self):
        return f"{self.flight.flight_number} - Seat {self.seat_number}"

    def is_available(self):
        """Check if seat is available for booking"""
        active_booking = self.bookings.filter(
            state__in=['SEAT_HELD', 'PAYMENT_PENDING', 'CONFIRMED']
        ).first()
        return active_booking is None


class Booking(models.Model):
    STATE_CHOICES = [
        ('INITIATED', 'Initiated'),
        ('SEAT_HELD', 'Seat Held'),
        ('PAYMENT_PENDING', 'Payment Pending'),
        ('CONFIRMED', 'Confirmed'),
        ('CANCELLED', 'Cancelled'),
        ('EXPIRED', 'Expired'),
        ('REFUNDED', 'Refunded'),
    ]

    # state transitions
    STATE_TRANSITIONS = {
        'INITIATED': ['SEAT_HELD'],
        'SEAT_HELD': ['PAYMENT_PENDING', 'EXPIRED'],
        'PAYMENT_PENDING': ['CONFIRMED', 'CANCELLED'],
        'CONFIRMED': ['CANCELLED'],
        'CANCELLED': ['REFUNDED'],
        'EXPIRED': [],
        'REFUNDED': [],
    }

    booking_reference = models.CharField(max_length=20, unique=True, db_index=True)
    flight = models.ForeignKey(Flight, on_delete=models.CASCADE, related_name='bookings')
    seat = models.ForeignKey(Seat, on_delete=models.CASCADE, related_name='bookings')
    passenger_name = models.CharField(max_length=255)
    passenger_email = models.EmailField()
    passenger_phone = models.CharField(max_length=20)
    state = models.CharField(max_length=20, choices=STATE_CHOICES, default='INITIATED', db_index=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    seat_held_at = models.DateTimeField(null=True, blank=True)
    payment_initiated_at = models.DateTimeField(null=True, blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    expired_at = models.DateTimeField(null=True, blank=True)
    refunded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'bookings'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['booking_reference']),
            models.Index(fields=['state', 'seat_held_at']),
        ]

    def __str__(self):
        return f"{self.booking_reference} - {self.passenger_name} ({self.state})"

    def can_transition_to(self, new_state):
        """Check if transition to new state is allowed"""
        allowed_states = self.STATE_TRANSITIONS.get(self.state, [])
        return new_state in allowed_states

    def transition_to(self, new_state):
        """Transition to a new state with validation"""
        if not self.can_transition_to(new_state):
            raise ValidationError(
                f"Cannot transition from {self.state} to {new_state}. "
                f"Allowed transitions: {self.STATE_TRANSITIONS.get(self.state, [])}"
            )
        
        old_state = self.state
        self.state = new_state

        now = timezone.now()
        timestamp_field_map = {
            'SEAT_HELD': 'seat_held_at',
            'PAYMENT_PENDING': 'payment_initiated_at',
            'CONFIRMED': 'confirmed_at',
            'CANCELLED': 'cancelled_at',
            'EXPIRED': 'expired_at',
            'REFUNDED': 'refunded_at',
        }
        
        if new_state in timestamp_field_map:
            setattr(self, timestamp_field_map[new_state], now)
        
        self.save()

        BookingStateHistory.objects.create(
            booking=self,
            from_state=old_state,
            to_state=new_state,
            notes=f"Transitioned from {old_state} to {new_state}"
        )

    def is_expired(self):
        """Check if seat hold has expired (10 minutes)"""
        if self.state == 'SEAT_HELD' and self.seat_held_at:
            expiry_time = self.seat_held_at + timedelta(minutes=10)
            return timezone.now() > expiry_time
        return False

    @property
    def hold_expires_at(self):
        """Calculate when the seat hold expires"""
        if self.state == 'SEAT_HELD' and self.seat_held_at:
            return self.seat_held_at + timedelta(minutes=10)
        return None


class BookingStateHistory(models.Model):
    """Track all state transitions for audit trail"""
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='state_history')
    from_state = models.CharField(max_length=20)
    to_state = models.CharField(max_length=20)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'booking_state_history'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.booking.booking_reference}: {self.from_state} → {self.to_state}"


class Payment(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
        ('REFUNDED', 'Refunded'),
    ]

    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='payments')
    transaction_id = models.CharField(max_length=50, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    payment_method = models.CharField(max_length=50, default='MOCK')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'payments'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.transaction_id} - {self.status}"


class Refund(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PROCESSED', 'Processed'),
        ('FAILED', 'Failed'),
    ]

    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='refunds')
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='refunds')
    refund_reference = models.CharField(max_length=50, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'refunds'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.refund_reference} - {self.status}"
