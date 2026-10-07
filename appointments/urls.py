from django.urls import path
from . import views

urlpatterns = [
    path('api/locations/', views.get_locations_api, name='api_get_locations'),
    path('api/locate-me/', views.locate_me_api, name='api_locate_me'),
    path('api/areas/', views.get_areas_api, name='api_get_areas'),
    path('api/hospitals/', views.get_hospitals_api, name='api_get_hospitals'),
    path('api/hospitals/nearby/', views.get_nearby_hospitals_api, name='api_hospitals_nearby'),
    path('api/hospitals/search/', views.search_hospitals_api, name='api_hospitals_search'),
    path('api/hospitals/<int:hospital_id>/', views.get_hospital_detail_api, name='api_hospital_detail'),
    path('api/specialties/', views.get_specialties_api, name='api_get_specialties'),
    path('api/doctors/', views.get_doctors_api, name='api_get_doctors'),
    path('api/doctors/search/', views.search_doctors_api, name='api_doctors_search'),
    path('api/appointments/slots/', views.get_available_slots_api, name='api_appointment_slots'),
    path('api/appointments/check-and-book/', views.check_and_book_appointment_api, name='api_check_and_book'),
    path('api/appointments/create/', views.check_and_book_appointment_api, name='api_create_appointment'),
    path('api/appointments/cancel/<int:booking_id>/', views.cancel_appointment_api, name='api_cancel_appointment'),
    path('api/location-pincode-sync/', views.api_location_pincode_sync, name='api_location_pincode_sync'),
    path('api/recommend-specialist/', views.api_recommend_specialist, name='api_recommend_specialist'),
    path('api/geocode/reverse/', views.reverse_geocode_api, name='api_reverse_geocode'),
]
