from rest_framework import serializers
from .models import Flight, Seat, Booking, Payment, Refund, BookingStateHistory


class FlightSerializer(serializers.ModelSerializer):
    available_seats = serializers.ReadOnlyField()

    class Meta:
        model = Flight
        fields = [
            'id', 'flight_number', 'origin', 'destination',
            'departure_time', 'arrival_time', 'total_seats',
            'available_seats', 'price', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class SeatSerializer(serializers.ModelSerializer):
    is_available = serializers.SerializerMethodField()

    class Meta:
        model = Seat
        fields = ['id', 'seat_number', 'seat_class', 'is_available']
        read_only_fields = ['id']

    def get_is_available(self, obj):
        return obj.is_available()


class BookingStateHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = BookingStateHistory
        fields = ['from_state', 'to_state', 'notes', 'created_at']


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = [
            'id', 'transaction_id', 'amount', 'status',
            'payment_method', 'created_at', 'processed_at'
        ]
        read_only_fields = ['id', 'transaction_id', 'created_at', 'processed_at']


class RefundSerializer(serializers.ModelSerializer):
    class Meta:
        model = Refund
        fields = [
            'id', 'refund_reference', 'amount', 'status',
            'reason', 'created_at', 'processed_at'
        ]
        read_only_fields = ['id', 'refund_reference', 'created_at', 'processed_at']


class BookingSerializer(serializers.ModelSerializer):
    flight_details = FlightSerializer(source='flight', read_only=True)
    seat_details = SeatSerializer(source='seat', read_only=True)
    state_history = BookingStateHistorySerializer(many=True, read_only=True)
    payments = PaymentSerializer(many=True, read_only=True)
    refunds = RefundSerializer(many=True, read_only=True)
    hold_expires_at = serializers.ReadOnlyField()

    class Meta:
        model = Booking
        fields = [
            'id', 'booking_reference', 'flight', 'seat',
            'passenger_name', 'passenger_email', 'passenger_phone',
            'state', 'amount', 'created_at', 'updated_at',
            'seat_held_at', 'payment_initiated_at', 'confirmed_at',
            'cancelled_at', 'expired_at', 'refunded_at',
            'hold_expires_at', 'flight_details', 'seat_details',
            'state_history', 'payments', 'refunds'
        ]
        read_only_fields = [
            'id', 'booking_reference', 'state', 'created_at',
            'updated_at', 'seat_held_at', 'payment_initiated_at',
            'confirmed_at', 'cancelled_at', 'expired_at', 'refunded_at'
        ]


class CreateBookingSerializer(serializers.Serializer):
    """Serializer for creating a new booking"""
    flight_id = serializers.IntegerField()
    seat_id = serializers.IntegerField()
    passenger_name = serializers.CharField(max_length=255)
    passenger_email = serializers.EmailField()
    passenger_phone = serializers.CharField(max_length=20)

    def validate(self, data):
        try:
            flight = Flight.objects.get(id=data['flight_id'])
        except Flight.DoesNotExist:
            raise serializers.ValidationError("Flight not found")

        try:
            seat = Seat.objects.get(id=data['seat_id'], flight=flight)
        except Seat.DoesNotExist:
            raise serializers.ValidationError("Seat not found for this flight")
        if not seat.is_available():
            raise serializers.ValidationError("Seat is not available")

        data['flight'] = flight
        data['seat'] = seat
        return data


class ProcessPaymentSerializer(serializers.Serializer):
    """Serializer for processing payment"""
    payment_method = serializers.CharField(max_length=50, default='MOCK')
    simulate_failure = serializers.BooleanField(default=False, required=False)


class CancelBookingSerializer(serializers.Serializer):
    """Serializer for cancelling a booking"""
    reason = serializers.CharField(max_length=500, required=False, allow_blank=True)


class BookingListSerializer(serializers.ModelSerializer):
    """Simplified serializer for listing bookings"""
    flight_number = serializers.CharField(source='flight.flight_number', read_only=True)
    seat_number = serializers.CharField(source='seat.seat_number', read_only=True)

    class Meta:
        model = Booking
        fields = [
            'id', 'booking_reference', 'flight_number', 'seat_number',
            'passenger_name', 'state', 'amount', 'created_at', 'hold_expires_at'
        ]
