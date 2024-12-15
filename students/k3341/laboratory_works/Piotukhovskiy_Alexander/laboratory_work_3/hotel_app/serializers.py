from datetime import datetime

from rest_framework import serializers
from .models import Client, Room, Employee, EmploymentContract, EmployeePosition, Reservation, CleaningSchedule


class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = ['id', 'passport_number', 'first_name', 'last_name', 'middle_name', 'city_from']


class RoomSerializer(serializers.ModelSerializer):
    type_id = serializers.IntegerField(source='type.id', read_only=True)
    type_name = serializers.CharField(source='type.name', read_only=True)
    current_client = serializers.SerializerMethodField()

    class Meta:
        model = Room
        fields = ['number', 'type_id', 'type_name', 'phone', 'current_client']

    def get_current_client(self, obj):
        if obj.status == 'AVAILABLE':
            return None

        reservation = Reservation.objects.filter(
            room=obj,
            status__in=['CONFIRMED', 'CHECKED_IN']
        ).order_by('-arrival_date').first()

        if reservation:
            return ClientSerializer(reservation.client).data

        return None


class ClientStayOverlapSerializer(serializers.Serializer):
    client_id = serializers.IntegerField(required=True)
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)

    def validate(self, data):
        start_date = data.get('start_date', None)
        end_date = data.get('end_date', None)

        if start_date and end_date and start_date > end_date:
            raise serializers.ValidationError("Дата окончания не может быть раньше даты начала.")

        return data


class CleaningEmployeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fields = ['id', 'first_name', 'last_name', 'middle_name']


class ClientRoomCleaningSerializer(serializers.Serializer):
    client_id = serializers.IntegerField(required=True)
    day_of_week = serializers.ChoiceField(choices=[
        ('MONDAY', 'Понедельник'),
        ('TUESDAY', 'Вторник'),
        ('WEDNESDAY', 'Среда'),
        ('THURSDAY', 'Четверг'),
        ('FRIDAY', 'Пятница'),
        ('SATURDAY', 'Суббота'),
        ('SUNDAY', 'Воскресенье'),
    ], required=True)

    def to_internal_value(self, data):
        data = data.copy()
        if 'day_of_week' in data:
            data['day_of_week'] = data['day_of_week'].upper()
        return super().to_internal_value(data)


class EmploymentContractDetailSerializer(serializers.ModelSerializer):
    employee_id = serializers.IntegerField(source='employee.id', read_only=True)
    employee_first_name = serializers.CharField(source='employee.first_name', read_only=True)
    employee_last_name = serializers.CharField(source='employee.last_name', read_only=True)
    employee_middle_name = serializers.CharField(source='employee.middle_name', read_only=True)
    position_id = serializers.IntegerField(source='position.id', read_only=True)
    position_name = serializers.CharField(source='position.name', read_only=True)

    class Meta:
        model = EmploymentContract
        fields = [
            'id',
            'contract_type',
            'employee_id',
            'employee_first_name',
            'employee_last_name',
            'employee_middle_name',
            'start_date',
            'end_date',
            'position_id',
            'position_name',
        ]


class HireEmployeeSerializer(serializers.Serializer):
    passport_number = serializers.CharField(max_length=10)
    first_name = serializers.CharField(max_length=50)
    last_name = serializers.CharField(max_length=50)
    middle_name = serializers.CharField(max_length=50, required=False, allow_blank=True)
    position_id = serializers.IntegerField()
    contract_type = serializers.ChoiceField(choices=EmploymentContract.CONTRACT_TYPE_CHOICES)
    start_date = serializers.DateField()
    end_date = serializers.DateField(required=False)

    def validate(self, data):
        contract_type = data['contract_type']
        end_date = data.get('end_date', None)
        start_date = data['start_date']

        if contract_type == 'PERMANENT' and end_date is not None:
            raise serializers.ValidationError({
                "end_date": "Поле не может быть указано для постоянного контракта (PERMANENT)."
            })

        if end_date and end_date <= start_date:
            raise serializers.ValidationError({
                "end_date": "Дата окончания должна быть позже даты начала контракта."
            })

        return data


class UpdateEmployeeSerializer(serializers.Serializer):
    employee_id = serializers.IntegerField(required=True)
    position_id = serializers.IntegerField(required=False)
    contract_type = serializers.ChoiceField(choices=EmploymentContract.CONTRACT_TYPE_CHOICES, required=False)
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)
    first_name = serializers.CharField(max_length=50, required=False)
    last_name = serializers.CharField(max_length=50, required=False)
    middle_name = serializers.CharField(max_length=50, required=False, allow_blank=True)
    passport_number = serializers.CharField(max_length=10, required=False)

    def validate(self, data):
        employee_id = data['employee_id']
        if not Employee.objects.filter(id=employee_id).exists():
            raise serializers.ValidationError({"employee_id": "Сотрудник с указанным ID не найден."})

        new_position_id = data.get('new_position_id')
        if new_position_id and not EmployeePosition.objects.filter(id=new_position_id).exists():
            raise serializers.ValidationError({"new_position_id": "Должность с указанным ID не найдена."})

        contract_type = data.get('new_contract_type')
        end_date = data.get('new_end_date')
        start_date = data.get('new_start_date')

        if contract_type == 'PERMANENT' and end_date is not None:
            raise serializers.ValidationError({
                "end_date": "Поле не может быть указано для постоянного контракта (PERMANENT)."
            })

        if end_date and start_date and end_date <= start_date:
            raise serializers.ValidationError({
                "new_end_date": "Дата окончания должна быть позже даты начала контракта."
            })

        return data


class FireEmployeeSerializer(serializers.Serializer):
    employee_id = serializers.IntegerField()
    termination_date = serializers.DateField(required=False)

    def validate(self, data):
        employee_id = data['employee_id']
        if not EmploymentContract.objects.filter(employee_id=employee_id, is_active=True).exists():
            raise serializers.ValidationError({"employee_id": "Активный контракт для указанного сотрудника не найден."})
        return data


class UpdateCleaningScheduleSerializer(serializers.Serializer):
    cleaner_id = serializers.IntegerField(required=True)
    cleaning_dates = serializers.ListField(
        child=serializers.DateField(),
        required=True,
        allow_empty=False
    )
    room_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=True,
        allow_empty=False
    )

    def validate_cleaner_id(self, value):
        if not EmploymentContract.objects.filter(employee_id=value, is_active=True).exists():
            raise serializers.ValidationError("Указанный служащий не найден или не имеет активного контракта.")
        return value

    def validate_room_ids(self, value):
        existing_numbers = set(Room.objects.filter(number__in=value).values_list('number', flat=True))
        missing_numbers = [room_number for room_number in value if room_number not in existing_numbers]

        if missing_numbers:
            raise serializers.ValidationError(
                {"missing_rooms": f"Следующие номера комнат не найдены: {', '.join(map(str, missing_numbers))}."}
            )

        return value


class CreateReservationSerializer(serializers.Serializer):
    passport_number = serializers.CharField(max_length=10, required=True)
    first_name = serializers.CharField(max_length=50, required=True)
    last_name = serializers.CharField(max_length=50, required=True)
    middle_name = serializers.CharField(max_length=50, required=False, allow_blank=True)
    city_from = serializers.CharField(max_length=50, required=True)
    room_number = serializers.IntegerField(required=True)
    arrival_date = serializers.DateField(required=True)
    departure_date = serializers.DateField(required=True)
    status = serializers.ChoiceField(choices=Reservation.STATUS_CHOICES, required=False)
    payment_status = serializers.ChoiceField(choices=Reservation.PAYMENT_STATUS_CHOICES, required=False)

    def validate(self, data):
        room_number = data['room_number']
        arrival_date = data['arrival_date']
        departure_date = data['departure_date']

        try:
            room = Room.objects.get(number=room_number)
        except Room.DoesNotExist:
            raise serializers.ValidationError({"room_number": f"Комната с номером {room_number} не найдена."})

        if room.status != 'AVAILABLE':
            raise serializers.ValidationError({"room_number": "Комната недоступна для заселения."})

        if departure_date <= arrival_date:
            raise serializers.ValidationError({"departure_date": "Дата выезда должна быть позже даты заселения."})

        data['room'] = room
        return data


class UpdateReservationSerializer(serializers.Serializer):
    arrival_date = serializers.DateField(required=False)
    departure_date = serializers.DateField(required=False)
    status = serializers.ChoiceField(choices=Reservation.STATUS_CHOICES, required=False)
    payment_status = serializers.ChoiceField(choices=Reservation.PAYMENT_STATUS_CHOICES, required=False)
    room_number = serializers.IntegerField(required=False)

    def validate(self, data):
        arrival_date = data.get('arrival_date')
        departure_date = data.get('departure_date')

        if arrival_date and departure_date and departure_date <= arrival_date:
            raise serializers.ValidationError(
                {"departure_date": "Дата выезда должна быть позже даты прибытия."}
            )

        if 'room_number' in data:
            try:
                room = Room.objects.get(number=data['room_number'])
                if room.status != 'AVAILABLE':
                    raise serializers.ValidationError(
                        {"room_number": f"Комната {data['room_number']} недоступна для бронирования."}
                    )
                data['room'] = room
            except Room.DoesNotExist:
                raise serializers.ValidationError(
                    {"room_number": f"Комната с номером {data['room_number']} не найдена."}
                )

        return data


class QuarterlyReportSerializer(serializers.Serializer):
    quarter = serializers.IntegerField(min_value=1, max_value=4, required=True)
    year = serializers.IntegerField(required=True)

    def validate(self, data):
        quarter = data['quarter']
        year = data['year']
        now = datetime.now()

        if year > now.year:
            raise serializers.ValidationError("Год не может быть в будущем.")

        if year == now.year:
            current_quarter = (now.month - 1) // 3 + 1
            if quarter > current_quarter:
                raise serializers.ValidationError(f"Нельзя запросить квартал {quarter}, так как он ещё не наступил.")

        return data


class ReservationSerializer(serializers.ModelSerializer):
    client = serializers.StringRelatedField(read_only=True)
    room = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Reservation
        fields = [
            'id',
            'client',
            'room',
            'admin',
            'booking_date',
            'arrival_date',
            'departure_date',
            'status',
            'payment_status',
            'price_at_booking',
            'final_price'
        ]


class EmployeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fields = [
            'id',
            'passport_number',
            'first_name',
            'last_name',
            'middle_name',
        ]


class CleaningScheduleSerializer(serializers.ModelSerializer):
    cleaner = serializers.StringRelatedField(read_only=True)
    room = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = CleaningSchedule
        fields = [
            'id',
            'cleaner',
            'room',
            'cleaning_date',
            'status'
        ]