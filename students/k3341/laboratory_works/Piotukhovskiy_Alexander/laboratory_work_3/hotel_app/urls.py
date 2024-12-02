from django.urls import path

from hotel_app.views import ClientsListView, RoomsByStatusView, ClientStayOverlapView, ClientRoomCleaningView, \
    EmployeeManagementView, CleaningScheduleManagementView, ReservationManagementView, QuarterlyReportView

urlpatterns = [
    path('clients', ClientsListView.as_view(), name='clients-list'),
    path('rooms', RoomsByStatusView.as_view(), name='available-rooms-count'),
    path('clients/stay-overlap', ClientStayOverlapView.as_view(), name='client-stay-overlap'),
    path('clients/room-cleaner', ClientRoomCleaningView.as_view(), name='client-room-cleaning'),
    path('employees/manage', EmployeeManagementView.as_view(), name='employee-management'),
    path('cleaning-schedules/manage', CleaningScheduleManagementView.as_view(), name='update-cleaning-schedule'),
    path('reservation', ReservationManagementView.as_view(), name='create-reservation'),
    path('reservation/<int:reservation_id>', ReservationManagementView.as_view(), name='update-reservation'),
    path('reports/quarterly', QuarterlyReportView.as_view(), name='quarterly-report'),
]