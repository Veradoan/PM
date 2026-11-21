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
        user = authenticate(
            request=self.context.get('request'),
            username=attrs['email'],
            password=attrs['password'],
        )

        if user is None:
            raise serializers.ValidationError(
                'Email hoặc mật khẩu không đúng.'
            )

        if not user.is_active:
            raise serializers.ValidationError(
                'Tài khoản đã bị khóa.'
            )

        attrs['user'] = user
        return attrs
