from django.contrib.auth import get_user_model, authenticate
from rest_framework import authentication, exceptions
from rest_framework.authentication import HTTP_HEADER_ENCODING
import base64
import binascii

class BasicAuthentication(authentication.BaseAuthentication):
    """
    DRF uchun HTTP Basic Authentication.
    """

    def authenticate(self, request):
        auth = authentication.get_authorization_header(request).split()

        if not auth or auth[0].lower() != b'basic':
            return None  # DRF uchun: None -> boshqa authenticatorga o‘tadi

        if len(auth) == 1:
            msg = 'Invalid basic header. No credentials provided.'
            raise exceptions.AuthenticationFailed(msg)
        elif len(auth) > 2:
            msg = 'Invalid basic header. Credentials string should not contain spaces.'
            raise exceptions.AuthenticationFailed(msg)

        try:
            auth_decoded = base64.b64decode(auth[1]).decode(HTTP_HEADER_ENCODING)
        except (TypeError, UnicodeDecodeError, binascii.Error):
            msg = 'Invalid basic header. Credentials not correctly base64 encoded.'
            raise exceptions.AuthenticationFailed(msg)

        userid, sep, password = auth_decoded.partition(':')
        if not sep:
            msg = 'Invalid basic header. Credentials string missing colon.'
            raise exceptions.AuthenticationFailed(msg)

        user = self.authenticate_credentials(userid, password, request)
        return (user, None)  # DRF tuple format: (user, auth)

    def authenticate_credentials(self, userid, password, request=None):
        """
        Foydalanuvchini tekshiradi va qaytaradi.
        """
        User = get_user_model()
        credentials = {
            User.USERNAME_FIELD: userid,
            'password': password
        }

        user = authenticate(request=request, **credentials)
        if user is None:
            raise exceptions.AuthenticationFailed('Invalid username/password.')
        if not user.is_active:
            raise exceptions.AuthenticationFailed('User inactive or deleted.')
        return user
