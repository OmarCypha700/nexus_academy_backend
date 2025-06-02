from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import RegisterView, LoginView, UserProfileView,InstructorDetailView, LogoutView # PasswordResetView, PasswordResetConfirmView

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("profile/", UserProfileView.as_view(), name="profile"),
    path("profile/update/", UserProfileView.as_view(), name="profile-update"),
    path("instructors/<int:pk>/", InstructorDetailView.as_view(), name="instructor-detail"),
    # path("reset-password/", PasswordResetView.as_view(), name="reset-password"),
    # path("reset-password-confirm/", PasswordResetConfirmView.as_view(), name="reset-password-confirm"),
    path("logout/", LogoutView.as_view(), name="logout"),
]
