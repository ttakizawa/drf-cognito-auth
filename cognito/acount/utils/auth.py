import logging

import jwt
import json
import requests
from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework import exceptions
import boto3

from django.apps import apps as django_apps
from django.conf import settings
from django.utils.encoding import smart_text
from django.utils.translation import ugettext as _
from django.core.cache import cache
from django.utils.functional import cached_property
from jwt.algorithms import RSAAlgorithm


logger = logging.getLogger(__name__)

AWS_REGION_NAME = getattr(settings, "AWS_REGION_NAME", None)
AWS_ACCESS_KEY_ID = getattr(settings, "AWS_ACCESS_KEY_ID", None)
AWS_SECRET_ACCESS_KEY = getattr(settings, "AWS_SECRET_ACCESS_KEY", None)
AWS_COGNITO_USER_POOL_ID = getattr(settings, "AWS_COGNITO_USER_POOL_ID", None)
AWS_COGNITO_APP_ID = getattr(settings, "AWS_COGNITO_APP_ID", None)


class CognitoAuthentication(BaseAuthentication):
    """Token based authentication using the JSON Web Token standard."""

    def authenticate(self, request):
        """Entrypoint for Django Rest Framework"""
        jwt_token = self.get_jwt_token(request)
        if jwt_token is None:
            return None

        # Authenticate token
        try:
            token_validator = self.get_token_validator(request)
            jwt_payload = token_validator.validate(jwt_token)
        except TokenError as e:
            print(str(e))
            raise exceptions.AuthenticationFailed()

        USER_MODEL = self.get_user_model()
        user = USER_MODEL.objects.get(username=jwt_payload['username'])
        return (user, jwt_token)

    def get_user_model(self):
        user_model = getattr(settings, "COGNITO_USER_MODEL", settings.AUTH_USER_MODEL)
        return django_apps.get_model(user_model, require_ready=False)

    def get_jwt_token(self, request):
        auth = get_authorization_header(request).split()
        if not auth or smart_text(auth[0].lower()) != "token":
            return None

        if len(auth) == 1:
            msg = _("Invalid Authorization header. No credentials provided.")
            raise exceptions.AuthenticationFailed(msg)
        elif len(auth) > 2:
            msg = _(
                "Invalid Authorization header. Credentials string "
                "should not contain spaces."
            )
            raise exceptions.AuthenticationFailed(msg)

        return auth[1]

    def get_token_validator(self, request):
        return TokenValidator(
            AWS_REGION_NAME,
            AWS_COGNITO_USER_POOL_ID,
            AWS_COGNITO_APP_ID,
        )

    def authenticate_header(self, request):
        """
        Method required by the DRF in order to return 401 responses for authentication failures, instead of 403.
        More details in https://www.django-rest-framework.org/api-guide/authentication/#custom-authentication.
        """
        return "Bearer: api"


class TokenError(Exception):
    pass


class TokenValidator:
    def __init__(self, aws_region, aws_user_pool, audience):
        self.aws_region = aws_region
        self.aws_user_pool = aws_user_pool
        self.audience = audience

    @cached_property
    def pool_url(self):
        return "https://cognito-idp.%s.amazonaws.com/%s" % (
            self.aws_region,
            self.aws_user_pool,
        )

    @cached_property
    def _json_web_keys(self):
        response = requests.get(f"{self.pool_url}/.well-known/jwks.json")
        response.raise_for_status()
        json_data = response.json()
        return {item["kid"]: json.dumps(item) for item in json_data["keys"]}

    def _get_public_key(self, token):
        try:
            headers = jwt.get_unverified_header(token)
        except jwt.DecodeError as exc:
            print(str(exc))
            raise TokenError(str(exc))

        if getattr(settings, "COGNITO_PUBLIC_KEYS_CACHING_ENABLED", False):
            cache_key = "django_cognito_jwt:%s" % headers["kid"]
            jwk_data = cache.get(cache_key)

            if not jwk_data:
                jwk_data = self._json_web_keys.get(headers["kid"])
                timeout = getattr(settings, "COGNITO_PUBLIC_KEYS_CACHING_TIMEOUT", 300)
                cache.set(cache_key, jwk_data, timeout=timeout)
        else:
            jwk_data = self._json_web_keys.get(headers["kid"])

        if jwk_data:
            return RSAAlgorithm.from_jwk(jwk_data)

    def validate(self, token):
        public_key = self._get_public_key(token)
        if not public_key:
            raise TokenError("No key found for this token")

        try:
            jwt_data = jwt.decode(
                token,
                public_key,
                #audience=self.audience,
                issuer=self.pool_url,
                algorithms=["RS256"],
            )
        except (jwt.InvalidTokenError, jwt.ExpiredSignature, jwt.DecodeError) as exc:
            print(str(exc))
            raise TokenError(str(exc))
        return jwt_data



def create_cognito_user(username, password):
    try:
        aws_client = boto3.client('cognito-idp',
            region_name = AWS_REGION_NAME,
            aws_access_key_id = AWS_ACCESS_KEY_ID,
            aws_secret_access_key = AWS_SECRET_ACCESS_KEY
        )

        # ユーザーの作成
        response = aws_client.admin_create_user(
            UserPoolId=AWS_COGNITO_USER_POOL_ID,
            Username=username,
            TemporaryPassword=password,
            MessageAction='SUPPRESS'
        )
        # ログインを試みる。（パスワードの変更を要求される。）
        response = aws_client.admin_initiate_auth(
            UserPoolId=AWS_COGNITO_USER_POOL_ID,
            ClientId=AWS_COGNITO_APP_ID,
            AuthFlow='ADMIN_NO_SRP_AUTH',
            AuthParameters={'USERNAME': username, 'PASSWORD': password},
        )
        session = response['Session']
        # パスワードを変更する。
        response = aws_client.admin_respond_to_auth_challenge(
            UserPoolId=AWS_COGNITO_USER_POOL_ID,
            ClientId=AWS_COGNITO_APP_ID,
            ChallengeName='NEW_PASSWORD_REQUIRED',
            ChallengeResponses={'USERNAME': username, 'NEW_PASSWORD': password},
            Session=session
        )

        return response
    except Exception as e:
        print(str(e))
        raise e


def get_access_token(request):
    try:
        aws_client = boto3.client('cognito-idp',
            region_name = AWS_REGION_NAME,
            aws_access_key_id = AWS_ACCESS_KEY_ID,
            aws_secret_access_key = AWS_SECRET_ACCESS_KEY
        )

        aws_result = aws_client.admin_initiate_auth(
            UserPoolId = AWS_COGNITO_USER_POOL_ID,
            ClientId = AWS_COGNITO_APP_ID,
            AuthFlow = "ADMIN_NO_SRP_AUTH",
            AuthParameters = {
                "USERNAME": request.data["username"],
                "PASSWORD": request.data["password"],
            }
        )

        # 認証完了
        return aws_result

    except Exception as e:
        print(str(e))
        # 認証失敗
        return None