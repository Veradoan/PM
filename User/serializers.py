from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import CustomUser

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        # 1. Tìm user bằng email để lấy username chuẩn xác
        try:
            user_obj = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            raise serializers.ValidationError("Tài khoản không tồn tại.")

        # 2. Sử dụng username thực tế của Django để authenticate thay vì nhét thẳng email
        user = authenticate(
            request=self.context.get('request'),
            username=user_obj.username, 
            password=password
        )

        if not user:
            raise serializers.ValidationError("Sai thông tin đăng nhập.")

        attrs['user'] = user
        return attrs

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        # Bắt buộc trả về 'role' để Frontend (React/Vue/JS) có cơ sở điều hướng giao diện
        fields = ['id', 'username', 'email', 'role']