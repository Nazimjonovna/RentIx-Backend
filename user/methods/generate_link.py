import base64
from decimal import Decimal
from dataclasses import dataclass

from user.models import Payment, Company  # Payment va Company

@dataclass
class GeneratePayLink:
    payment: Payment  # Payment modeli orqali ishlaydi

    def generate_link(self) -> str:
        """
        Payment va kompaniya parametrlariga asoslanib Payme link yaratadi.
        Callback URL ham Company modeldan olinadi.
        """
        company: Company = self.payment.company  # Payment bilan bog‘langan Company

        if not company.payme_id:
            raise ValueError("Kompaniya uchun payme_id mavjud emas")
        if not company.payme_callback_url:
            raise ValueError("Kompaniya uchun payme_callback_url mavjud emas")

        PAYME_ID = company.payme_id
        PAYME_ACCOUNT = company.payme_id  # agar account ham payme_id bilan bir xil bo‘lsa
        PAYME_CALL_BACK_URL = company.payme_callback_url  # modeldan olinadi
        PAYME_URL = "https://checkout.paycom.uz"  # default Payme URL

        GENERETED_PAY_LINK: str = "{payme_url}/{encode_params}"
        PARAMS: str = 'm={payme_id};ac.{payme_account}={order_id};a={amount};c={call_back_url}'

        # Payment modeldan ma'lumot olish
        order_id = self.payment.order.id if self.payment.order else self.payment.order_id
        amount = self.to_tiyin(Decimal(self.payment.amount))  # som → tiyin

        PARAMS = PARAMS.format(
            payme_id=PAYME_ID,
            payme_account=PAYME_ACCOUNT,
            order_id=order_id,
            amount=int(amount),
            call_back_url=PAYME_CALL_BACK_URL
        )

        encode_params = base64.b64encode(PARAMS.encode("utf-8"))
        return GENERETED_PAY_LINK.format(
            payme_url=PAYME_URL,
            encode_params=encode_params.decode('utf-8')
        )

    @staticmethod
    def to_soum(amount: Decimal) -> Decimal:
        """Tiyindan so‘mga o‘tkazadi"""
        return amount / 100

    @staticmethod
    def to_tiyin(amount: Decimal) -> Decimal:
        """So‘mdan tiyinga o‘tkazadi"""
        return amount * 100
