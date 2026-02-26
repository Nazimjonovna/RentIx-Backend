import time
from django.db import transaction
from user.utils.get_params import get_params

from user.models import Payment  
from user.serializers import PaymentSerializer  
from user.exceptions import PerformTransactionDoesNotExist


class CancelTransaction:

    @transaction.atomic
    def __call__(self, params: dict):

        # Serializer tekshiruv
        serializer = PaymentSerializer(
            data=get_params(params)
        )
        serializer.is_valid(raise_exception=True)
        clean_data = serializer.validated_data

        transaction_id = clean_data.get("transaction_id")

        # Transactionni olish
        payment: Payment = Payment.objects.filter(
            transaction_id=transaction_id
        ).first()

        if not payment:
            raise PerformTransactionDoesNotExist()

        with transaction.atomic():

            # agar hali perform bo‘lmagan bo‘lsa (xperform_time == 0)
            if payment.xperform_time == 0:
                payment.state = -1  # bekor qilingan (lekin pul o‘tmagan)
            
            # agar allaqachon amalga oshirilgan bo‘lsa
            else:
                payment.state = -2  # qaytarish imkoni yo‘q (pul o‘tgan)

            # cancel_time
            if payment.cancel_time == 0:
                payment.cancel_time = int(time.time() * 1000)

            # Reason
            payment.reason = clean_data.get("reason")

            payment.save()

        # Payme uchun javob
        response = {
            "result": {
                "state": payment.state,
                "cancel_time": payment.cancel_time,
                "transaction": payment.transaction_id,
                "reason": int(payment.reason or 0),
            }
        }

        return response
