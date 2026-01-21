from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.core.exceptions import ValidationError

from .models import Flight, Booking
from .serializers import (
    FlightSerializer, SeatSerializer, BookingSerializer,
    CreateBookingSerializer, ProcessPaymentSerializer,
    CancelBookingSerializer, BookingListSerializer
)
from .services import BookingService, SeatAvailabilityService


class FlightViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing flights
    """
    queryset = Flight.objects.all()
    serializer_class = FlightSerializer

    @action(detail=True, methods=['get'])
    def available_seats(self, request, pk=None):
        flight = self.get_object()
        available_seats = SeatAvailabilityService.get_available_seats(flight)
        serializer = SeatSerializer(available_seats, many=True)
        return Response(serializer.data)


class BookingViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing bookings with state machine
    """
    queryset = Booking.objects.all()
    lookup_field = 'booking_reference'

    def get_serializer_class(self):
        if self.action == 'list':
            return BookingListSerializer
        return BookingSerializer

    def get_queryset(self):
        """
        Optionally filter bookings by state
        """
        queryset = Booking.objects.select_related('flight', 'seat').prefetch_related(
            'state_history', 'payments', 'refunds'
        )
        
        state = self.request.query_params.get('state', None)
        if state:
            queryset = queryset.filter(state=state)
        
        return queryset

    def create(self, request):
        """
        Create a new booking
        """
        serializer = CreateBookingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            booking = BookingService.create_booking(
                flight=serializer.validated_data['flight'],
                seat=serializer.validated_data['seat'],
                passenger_name=serializer.validated_data['passenger_name'],
                passenger_email=serializer.validated_data['passenger_email'],
                passenger_phone=serializer.validated_data['passenger_phone']
            )

            booking = BookingService.hold_seat(booking)

            response_serializer = BookingSerializer(booking)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)

        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def initiate_payment(self, request, booking_reference=None):
        """
        Initiate payment for a booking
        """
        booking = self.get_object()
        serializer = ProcessPaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            booking, payment = BookingService.initiate_payment(
                booking=booking,
                payment_method=serializer.validated_data.get('payment_method', 'MOCK')
            )

            response_serializer = BookingSerializer(booking)
            return Response(response_serializer.data, status=status.HTTP_200_OK)

        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def process_payment(self, request, booking_reference=None):
        """
        Process payment for a booking (mocked)
        """
        booking = self.get_object()
        serializer = ProcessPaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            payment = booking.payments.filter(status='PENDING').first()
            if not payment:
                return Response(
                    {'error': 'No pending payment found'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            booking, payment = BookingService.process_payment(
                booking=booking,
                payment=payment,
                simulate_failure=serializer.validated_data.get('simulate_failure', False)
            )

            response_serializer = BookingSerializer(booking)
            return Response({
                'booking': response_serializer.data,
                'payment_status': payment.status,
                'message': 'Payment processed successfully' if payment.status == 'SUCCESS' else 'Payment failed'
            }, status=status.HTTP_200_OK)

        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def cancel(self, request, booking_reference=None):
        """
        Cancel a confirmed booking
        """
        booking = self.get_object()
        serializer = CancelBookingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            booking = BookingService.cancel_booking(
                booking=booking,
                reason=serializer.validated_data.get('reason', '')
            )

            response_serializer = BookingSerializer(booking)
            return Response(response_serializer.data, status=status.HTTP_200_OK)

        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def refund(self, request, booking_reference=None):
        """
        Process refund for a cancelled booking
        """
        booking = self.get_object()
        serializer = CancelBookingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            booking, refund = BookingService.process_refund(
                booking=booking,
                reason=serializer.validated_data.get('reason', '')
            )

            response_serializer = BookingSerializer(booking)
            return Response({
                'booking': response_serializer.data,
                'refund_reference': refund.refund_reference,
                'refund_amount': str(refund.amount),
                'message': 'Refund processed successfully'
            }, status=status.HTTP_200_OK)

        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['post'])
    def expire_holds(self, request):
        """
        Manually trigger expiration of old seat holds
        """
        expired_count = BookingService.expire_old_seat_holds()
        return Response({
            'message': f'Expired {expired_count} seat holds',
            'count': expired_count
        }, status=status.HTTP_200_OK)
