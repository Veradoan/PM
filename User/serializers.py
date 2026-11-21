from django.contrib.auth import authenticate
from rest_framework import serializers

from .models import CustomUser


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = [
            'id',
            'username',
            'email',
            'first_name',
            'last_name',
            'role',
        ]
        read_only_fields = ['id', 'username', 'role']


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
            raise serializers.ValidationError("Email hoặc mật khẩu không đúng.")

        if not user_obj.is_active:
            raise serializers.ValidationError("Tài khoản đã bị khóa.")

        # 2. Authenticate bằng username thực tế của Django
        user = authenticate(
            request=self.context.get('request'),
            username=user_obj.username,
            password=password,
        )

        if not user:
            raise serializers.ValidationError("Email hoặc mật khẩu không đúng.")

        attrs['user'] = user
        return attrs