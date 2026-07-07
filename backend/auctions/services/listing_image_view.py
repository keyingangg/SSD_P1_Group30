"""Listing image upload API (diagram: svc_listing_image)."""
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.services.permissions import IsAdminUser

from core.cross_cutting.storage import upload_image


class ListingImageUploadView(APIView):
    """Upload a listing image to a private Supabase Storage bucket (admin only)."""

    permission_classes = [IsAdminUser]
    staff_only = True
    parser_classes = [MultiPartParser]

    def post(self, request):
        f = request.FILES.get("file")
        if not f:
            return Response({"detail": "No file provided."}, status=400)

        # upload_image validates size, real MIME type, and extension
        # server-side, and stores the file under a server-generated UUID
        # name (NFSR-IN-04 / NFSR-C-07 / NFSR-C-02). Any ValidationError it
        # raises is converted to a 400 by core.cross_cutting.exceptions.custom_exception_handler.
        object_key = upload_image(f, f.name)
        return Response({"key": object_key}, status=201)
