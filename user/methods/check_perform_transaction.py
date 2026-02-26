from user.utils.get_params import get_params
from user.serializers import PaymentSerializer
from user.models import Order
from user.exceptions import (
    PerformTransactionDoesNotExist,
    IncorrectAmount
)


class CheckPerformTransaction:

    def __call__(self, params: dict) -> dict:

        data = get_params(params)

        order_id = data.get("order_id")
        amount = data.get("amount")

        # 1️⃣ Order mavjudligini tekshirish
        try:
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            raise PerformTransactionDoesNotExist()

        # 2️⃣ Summaning to‘g‘ri ekanligini tekshirish
        if float(order.amount) != float(amount):
            raise IncorrectAmount()

        # 3️⃣ Hammasi to‘g‘ri bo‘lsa
        return {
            "result": {
                "allow": True
            }
        }
