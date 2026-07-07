"""User profile read API (diagram: svc_profile)."""
from rest_framework.response import Response
from rest_framework.views import APIView

from .permissions import IsEmailVerified
from .serializers import UserProfileSerializer


class UserProfileView(APIView):
    """Read the authenticated user's own profile."""

    permission_classes = [IsEmailVerified]

    def get(self, request):
        return Response(UserProfileSerializer(request.user).data, status=200)
