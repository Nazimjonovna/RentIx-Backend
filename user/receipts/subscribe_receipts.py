import json
import requests
from decimal import Decimal
from User.models import Payment, Company

class PaymeSubscribeReceipts:
    """
    Payme Subscribe Receipts klassi Payment va Company modeliga mos
    """

    def __init__(self, payment: Payment):
        self.payment = payment
        self.company: Company = payment.company

        if not self.company.payme_id:
            raise ValueError("Kompaniya uchun payme_id mavjud emas")
        if not getattr(self.company, 'payme_key', None):
            raise ValueError("Kompaniya uchun payme_key mavjud emas")

        self.__base_url = "https://checkout.paycom.uz/api"  # default Payme API URL
        self.__headers = {
            "X-Auth": f"{self.company.payme_id}:{self.company.payme_key}"
        }
        self.__methods = {
            "receipts_get": "receipts.get",
            "receipts_pay": "receipts.pay",
            "receipts_send": "receipts.send",
            "receipts_check": "receipts.check",
            "receipts_cancel": "receipts.cancel",
            "receipts_create": "receipts.create",
            "receipts_get_all": "receipts.get_all",
        }

    def __request(self, data: dict) -> dict:
        """Private method to request Payme API"""
        req_data = {
            "data": data,
            "url": self.__base_url,
            "headers": self.__headers,
        }
        return requests.post(**req_data).json()

    def create_receipt(self) -> dict:
        """Payment modeldagi amount va order_id orqali yangi receipt yaratadi"""
        amount = int(self.payment.amount * 100)  # som → tiyin
        order_id = self.payment.order.id if self.payment.order else self.payment.order_id

        data = {
            "method": self.__methods.get("receipts_create"),
            "params": {
                "amount": amount,
                "account": {
                    "order_id": order_id
                }
            }
        }
        return self.__request(self._parse_to_json(**data))

    def pay_receipt(self, invoice_id: str, token: str, phone: str) -> dict:
        data = {
            "method": self.__methods.get("receipts_pay"),
            "params": {
                "id": invoice_id,
                "token": token,
                "payer": {
                    "phone": phone
                }
            }
        }
        return self.__request(self._parse_to_json(**data))

    def send_receipt(self, invoice_id: str, phone: str) -> dict:
        data = {
            "method": self.__methods.get("receipts_send"),
            "params": {
                "id": invoice_id,
                "phone": phone
            }
        }
        return self.__request(self._parse_to_json(**data))

    def cancel_receipt(self, invoice_id: str) -> dict:
        data = {
            "method": self.__methods.get("receipts_cancel"),
            "params": {
                "id": invoice_id
            }
        }
        return self.__request(self._parse_to_json(**data))

    def check_receipt(self, invoice_id: str) -> dict:
        data = {
            "method": self.__methods.get("receipts_check"),
            "params": {
                "id": invoice_id
            }
        }
        return self.__request(self._parse_to_json(**data))

    @staticmethod
    def _parse_to_json(**kwargs) -> dict:
        """Convert data to JSON"""
        data = {
            "method": kwargs.pop("method"),
            "params": kwargs.pop("params"),
        }
        return json.dumps(data)
