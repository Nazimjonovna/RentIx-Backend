import base64
from decimal import Decimal
from Payment.models import Company  # sizning Company modeli

class PayComResponse:
    LINK = 'https://checkout.paycom.uz'

    def __init__(self, company_id: int):
        # Company ma'lumotlarini olish
        self.company = Company.objects.get(id=company_id)
        if not self.company.payme_id:
            raise ValueError("Company Payme ID not set.")
        if not self.company.payme_account:
            raise ValueError("Company Payme Account not set.")
        if not self.company.payme_callback_url:
            raise ValueError("Company Payme callback URL not set.")

        self.TOKEN = self.company.payme_id
        self.KEY = self.company.payme_account
        self.RETURN_URL = self.company.payme_callback_url

    def create_initialization(self, amount: Decimal, order_id: str) -> str:
        """
        Dinamik Company parametrlari bilan Payme to'lov linkini yaratadi.
        """
        params = f"m={self.TOKEN};ac.{self.KEY}={order_id};a={amount};c={self.RETURN_URL}"
        encode_params = base64.b64encode(params.encode("utf-8")).decode('utf-8')
        url = f"{self.LINK}/{encode_params}"
        return url
