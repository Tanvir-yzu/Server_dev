# accounts/urls.py
from django.urls import path
from .views import (
    RegisterView,
    LoginView,
    ProfileView,
    EditProfileView,
    logout_view,
)

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', logout_view, name='logout'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('edit-profile/', EditProfileView.as_view(), name='edit_profile'),
    path('edit-profile/<int:pk>/', EditProfileView.as_view(), name='edit_profile'),
]