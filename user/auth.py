from django.contrib.auth import get_user_model, authenticate
from rest_framework import authentication, exceptions
from rest_framework.authentication import HTTP_HEADER_ENCODING
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken

import base64
import binascii

from .models import User, Company, Manager


class BasicAuthentication(authentication.BaseAuthentication):
    """
    DRF uchun HTTP Basic Authentication
    """

    def authenticate(self, request):
        auth = authentication.get_authorization_header(request).split()

        if not auth or auth[0].lower() != b"basic":
            return None

        if len(auth) == 1:
            raise exceptions.AuthenticationFailed(
                "Invalid basic header. No credentials provided."
            )

        elif len(auth) > 2:
            raise exceptions.AuthenticationFailed(
                "Invalid basic header. Credentials string should not contain spaces."
            )

        try:
            auth_decoded = base64.b64decode(auth[1]).decode(HTTP_HEADER_ENCODING)

        except (TypeError, UnicodeDecodeError, binascii.Error):
            raise exceptions.AuthenticationFailed(
                "Invalid basic header. Credentials not correctly base64 encoded."
            )

        userid, sep, password = auth_decoded.partition(":")

        if not sep:
            raise exceptions.AuthenticationFailed(
                "Invalid basic header. Credentials string missing colon."
            )

        user = self.authenticate_credentials(userid, password, request)

        return (user, None)

    def authenticate_credentials(self, userid, password, request=None):
        UserModel = get_user_model()

        credentials = {
            UserModel.USERNAME_FIELD: userid,
            "password": password
        }

        user = authenticate(request=request, **credentials)

        if user is None:
            raise exceptions.AuthenticationFailed("Invalid username/password.")

        if not user.is_active:
            raise exceptions.AuthenticationFailed("User inactive or deleted.")

        return user


class CustomJWTAuthentication(JWTAuthentication):
    """
    JWT auth:
    User
    Company (admin)
    Manager
    """

    def authenticate(self, request):
        header = self.get_header(request)

        if header is None:
            return None

        raw_token = self.get_raw_token(header)

        if raw_token is None:
            return None

        validated_token = self.get_validated_token(raw_token)

        user = self.get_user(validated_token)

        return (user, validated_token)

    def get_user(self, validated_token):
        role = validated_token.get("role")

        if role:
            role = str(role).lower()

      
        if role in ["superadmin", "user"] or not role:
            user_id = validated_token.get("user_id")

            if not user_id:
                raise InvalidToken(
                    "Token contained no recognizable user identification"
                )

            try:
                return User.objects.get(id=user_id)

            except User.DoesNotExist:
                raise InvalidToken("User not found")

        
        if role == "admin":
            company_id = validated_token.get("company_id")

            if not company_id:
                raise InvalidToken("Company ID not found")

            try:
                company = Company.objects.get(id=company_id)
                return company

            except Company.DoesNotExist:
                raise InvalidToken("Company not found")

        
        if role == "manager":
            manager_id = validated_token.get("manager_id")

            if not manager_id:
                raise InvalidToken("Manager ID not found")

            try:
                manager = Manager.objects.get(id=manager_id)
                return manager

            except Manager.DoesNotExist:
                raise InvalidToken("Manager not found")

        raise InvalidToken("Unknown role")