import uuid
import time
import datetime

from user.utils.get_params import get_params
from user.exceptions import TooManyRequests

from user.models import Payment  # app nomi User


class CreateTransaction:

    def __call__(self, params: dict) -> dict:
        data = get_params(params)
        order_id = data.get("order_id")
        transaction_id_input = data.get("_id")
        amount = data.get("amount")

        if not order_id or not transaction_id_input or amount is None:
            raise ValueError("order_id, _id va amount majburiy")

        # 1️⃣ Order bo‘yicha oxirgi transactionni olish
        transaction = Payment.objects.filter(
            order_id=order_id
        ).last()

        # 2️⃣ TooManyRequests tekshiruvi
        if transaction and transaction._id != transaction_id_input:
            raise TooManyRequests()

        # 3️⃣ Yangi transaction yaratish
        if not transaction:
            transaction = Payment.objects.create(
                _id=transaction_id_input,
                order_id=order_id,
                transaction_id=str(uuid.uuid4()),
                amount=amount,
                created_at_ms=int(time.time() * 1000),
                state=1  # yangi transaction
            )

        # 4️⃣ Javobni tayyorlash
        response = {
            "result": {
                "create_time": int(transaction.created_at_ms),
                "transaction": transaction.transaction_id,
                "state": int(transaction.state),
            }
        }

        return response

    @staticmethod
    def _convert_ms_to_datetime(time_ms: int) -> datetime.datetime:
        """Convert from milliseconds to datetime object"""
        return datetime.datetime.fromtimestamp(time_ms / 1000)
