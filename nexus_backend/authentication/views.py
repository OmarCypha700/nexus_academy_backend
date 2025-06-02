from django.conf import settings
from rest_framework.views import APIView 
from rest_framework import generics, permissions, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.auth import get_user_model
from .serializers import RegisterSerializer, InstructorSerializer, ProfileSerializer, PasswordResetSerializer, PasswordResetConfirmSerializer
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.template.loader import render_to_string

User = get_user_model()

# User Registration
class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

# User Login
class LoginView(TokenObtainPairView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        print(f"Request data: {request.data}")  # Log incoming data for debugging

        response = super().post(request, *args, **kwargs)
        return Response({
            "access": response.data.get("access"),
            "refresh": response.data.get("refresh"),
            "message": "Login successful"
        }, status=status.HTTP_200_OK)
    
class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = ProfileSerializer(request.user)
        print("Profile view accessed by:", self.request.user)
        print("Profile:", serializer.data)
        return Response(serializer.data)

    def put(self, request):
        serializer = ProfileSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class InstructorDetailView(generics.RetrieveAPIView):
    queryset = User.objects.filter(role="instructor")
    serializer_class = InstructorSerializer
    permission_classes = [IsAuthenticated]


# Logout (Blacklist Token)
class LogoutView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            if not refresh_token:
                return Response({"error": "Refresh token is required"}, status=status.HTTP_400_BAD_REQUEST)
                
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({"message": "Logged out successfully"}, status=status.HTTP_200_OK)
        except TokenError:
            return Response({"error": "Invalid token"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# class PasswordResetView(APIView):
#     permission_classes = [permissions.AllowAny]

#     def post(self, request, *args, **kwargs):
#         serializer = PasswordResetSerializer(data=request.data)
#         serializer.is_valid(raise_exception=True)
#         user = serializer.validated_data['user']
#         token = serializer.validated_data['token']

#         # user = serializer.get_user()

#         uid = urlsafe_base64_encode(force_bytes(user.pk))
#         # token = default_token_generator.make_token(user)
#         reset_url = f"{settings.FRONTEND_URL}/reset-password-confirm/{uid}/{token}"

#         subject = "Reset Your Password - Nexus Academy"
#         message = render_to_string("authentication/emails/password_reset_email.html", {
#             "user": user,
#             "reset_url": reset_url,
#             "site_name": settings.SITE_NAME,
#         })

#         send_mail(
#             subject,
#             message,
#             settings.DEFAULT_FROM_EMAIL,
#             [user.email],
#             fail_silently=False,
#         )

#         return Response({"message": "Password reset email sent."}, status=status.HTTP_200_OK)
    

# class PasswordResetConfirmView(APIView):
#     def post(self, request, *args, **kwargs):
#         serializer = PasswordResetConfirmSerializer(data=request.data)
#         if serializer.is_valid():
#             serializer.save()
#             return Response({"message": "Password has been reset successfully."}, status=status.HTTP_200_OK)
#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)