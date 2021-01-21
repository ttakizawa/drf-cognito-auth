from django.db import transaction
from rest_framework import authentication, permissions, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, viewsets, filters

from .utils.auth import CognitoAuthentication, get_access_token
from .serializer import AccountSerializer
from .models import AccountManager, Account

class LoginAPIView(APIView):

    authentication_classes = [CognitoAuthentication,]

    def post(self, request, *args, **kwargs):
        try:
            token = get_access_token(request=request)
            response = Response(
                {
                    "access_token": token["AuthenticationResult"]["AccessToken"],
                    "refresh_token": token["AuthenticationResult"]["RefreshToken"],
                },
                status=status.HTTP_200_OK
            )
            return response
        except Exception as e:
            print(str(e))
            return Response({"message": "error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SignUpAPIView(generics.CreateAPIView):
    permission_classes = (permissions.AllowAny,)
    queryset = Account.objects.all()
    serializer_class = AccountSerializer

    @transaction.atomic
    def post(self, request, format=None):
        serializer = AccountSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class NotLoginRequiredAPIView(APIView):

    permission_classes = (permissions.AllowAny,)

    def get(self, request):
        return Response(
                {
                    "message": "notLoginRequired",
                },
                status=status.HTTP_200_OK
            )

class LoginRequiredAPIView(APIView):

    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        return Response(
                {
                    "message": "Authenticated Access",
                },
                status=status.HTTP_200_OK
            )