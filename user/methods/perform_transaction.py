import time

from user.models import Payment
from user.utils.get_params import get_params
from user.utils.logger import logged

class PerformTransaction:

    def __call__(self, params: dict) -> dict:
        data = get_params(params)
        transaction_id_input = data.get("_id") or data.get("id")
        response: dict = None

        if not transaction_id_input:
            logged("transaction_id not provided", "error")
            return None

        try:
            logged_message = "started check trx in db (perform_transaction)"
            payment: Payment = Payment.objects.get(_id=transaction_id_input)
            logged(logged_message=logged_message, logged_type="info")

            # 1️⃣ Transactionni perform qilish
            payment.state = 2  # payment tasdiqlangan
            if payment.perform_time == 0:
                payment.perform_time = int(time.time() * 1000)

            payment.save()

            # 2️⃣ Javobni tayyorlash
            response = {
                "result": {
                    "perform_time": int(payment.perform_time),
                    "transaction": payment.transaction_id,
                    "state": int(payment.state),
                }
            }

        except Payment.DoesNotExist:
            logged(
                logged_message=f"Payment with _id={transaction_id_input} does not exist",
                logged_type="error"
            )
        except Exception as e:
            logged(
                logged_message=f"Error during perform transaction: {e} | {transaction_id_input}",
                logged_type="error"
            )

        return response
