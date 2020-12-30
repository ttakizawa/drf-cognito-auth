from django.contrib.auth import update_session_auth_hash
from rest_framework import serializers

from .models import Account, AccountManager
from .utils.auth import create_cognito_user


class AccountSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = Account
        fields = ('id', 'username', 'password')

    def create(self, validated_data):
        response = create_cognito_user(validated_data['username'], validated_data['password'])
        print(response)
        return Account.objects.create_user(request_data=validated_data)