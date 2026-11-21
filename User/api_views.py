from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import LoginSerializer, UserSerializer
from rest_framework.decorators import api_view, permission_classes
from .permissions import IsAdmin
from .models import CustomUser
@api_view(['POST'])
@permission_classes([IsAdmin]) # BẮT BUỘC CHỈ ADMIN MỚI ĐƯỢC GỌI API NÀY
def change_user_role(request, user_id):
    try:
        user = CustomUser.objects.get(id=user_id)
        new_role = request.data.get('role')
        
        # Validation chặt chẽ các role hợp lệ
        if new_role not in ['student', 'moderator', 'admin']:
            return Response({"error": "Role không hợp lệ."}, status=400)
            
        user.role = new_role
        user.save()
        return Response({"message": f"Đã cập nhật role thành {new_role} cho {user.email}"}, status=200)
        
    except CustomUser.DoesNotExist:
        return Response({"error": "Không tìm thấy người dùng."}, status=404)
class LoginAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginSerializer(
            data=request.data,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data['user']
        refresh = RefreshToken.for_user(user)

        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': UserSerializer(user).data,
        }, status=status.HTTP_200_OK)


class MeAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)
