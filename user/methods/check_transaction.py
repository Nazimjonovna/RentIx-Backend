from user.utils.logger import logged
from user.utils.get_params import get_params

from user.models import Payment  
# Bu metodda serializer shart emas — biz transaction_id orqali qidiramiz

class CheckTransaction:

    def __call__(self, params: dict) -> dict:
        response = None

        data = get_params(params)
        transaction_id = data.get("id") or data.get("transaction_id")

        if not transaction_id:
            logged("transaction_id not provided", "error")
            return None

        try:
            logged("started check transaction in db", "info")

            payment: Payment = Payment.objects.get(
                transaction_id=transaction_id
            )

            response = {
                "result": {
                    "create_time": int(payment.created_at_ms) if payment.created_at_ms else 0,
                    "perform_time": payment.xperform_time,
                    "cancel_time": payment.cancel_time,
                    "transaction": payment.transaction_id,
                    "state": payment.state,
                    "reason": None,
                }
            }

            if payment.reason:
                response["result"]["reason"] = int(payment.reason)

        except Exception as e:
            logged(
                logged_message=f"error during get transaction in db {e} | {transaction_id}",
                logged_type="error"
            )

        return response
