from datetime import time
from .models import Filial, CompanyWorkDay


def create_default_filial_and_workdays(company):
    filial, created = Filial.objects.get_or_create(
        company=company,
        name="Default filial",
        defaults={
            "address": None,
            "phone": company.phone1,
        }
    )

    for weekday in range(7):
        CompanyWorkDay.objects.get_or_create(
            company=company,
            filial=filial,
            weekday=weekday,
            defaults={
                "start_time": time(9, 0),
                "end_time": time(18, 0),
                "is_working": True,
                "is_24_7": False,
            }
        )

    return filial