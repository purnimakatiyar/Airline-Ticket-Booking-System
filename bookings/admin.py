from django.contrib import admin
from .models import Flight, Seat, Booking, BookingStateHistory, Payment, Refund

# Register your models here.


@admin.register(Flight)
class FlightAdmin(admin.ModelAdmin):
    list_display = ['flight_number', 'origin', 'destination', 'departure_time', 'total_seats', 'available_seats', 'price']
    list_filter = ['origin', 'destination', 'departure_time']
    search_fields = ['flight_number', 'origin', 'destination']
    ordering = ['-departure_time']


@admin.register(Seat)
class SeatAdmin(admin.ModelAdmin):
    list_display = ['seat_number', 'flight', 'seat_class', 'is_available']
    list_filter = ['seat_class', 'flight']
    search_fields = ['seat_number', 'flight__flight_number']


class BookingStateHistoryInline(admin.TabularInline):
    model = BookingStateHistory
    extra = 0
    readonly_fields = ['from_state', 'to_state', 'notes', 'created_at']
    can_delete = False


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    readonly_fields = ['transaction_id', 'amount', 'status', 'created_at', 'processed_at']
    can_delete = False


class RefundInline(admin.TabularInline):
    model = Refund
    extra = 0
    readonly_fields = ['refund_reference', 'amount', 'status', 'created_at', 'processed_at']
    can_delete = False


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = [
        'booking_reference', 'passenger_name', 'flight', 
        'seat', 'state', 'amount', 'created_at'
    ]
    list_filter = ['state', 'created_at', 'flight']
    search_fields = ['booking_reference', 'passenger_name', 'passenger_email']
    readonly_fields = [
        'booking_reference', 'state', 'created_at', 'updated_at',
        'seat_held_at', 'payment_initiated_at', 'confirmed_at',
        'cancelled_at', 'expired_at', 'refunded_at'
    ]
    inlines = [BookingStateHistoryInline, PaymentInline, RefundInline]
    ordering = ['-created_at']

    fieldsets = (
        ('Booking Information', {
            'fields': ('booking_reference', 'flight', 'seat', 'amount', 'state')
        }),
        ('Passenger Information', {
            'fields': ('passenger_name', 'passenger_email', 'passenger_phone')
        }),
        ('Timestamps', {
            'fields': (
                'created_at', 'updated_at', 'seat_held_at',
                'payment_initiated_at', 'confirmed_at', 'cancelled_at',
                'expired_at', 'refunded_at'
            )
        }),
    )


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['transaction_id', 'booking', 'amount', 'status', 'payment_method', 'created_at']
    list_filter = ['status', 'payment_method', 'created_at']
    search_fields = ['transaction_id', 'booking__booking_reference']
    readonly_fields = ['transaction_id', 'created_at', 'updated_at', 'processed_at']


@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    list_display = ['refund_reference', 'booking', 'amount', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['refund_reference', 'booking__booking_reference']
    readonly_fields = ['refund_reference', 'created_at', 'processed_at']
