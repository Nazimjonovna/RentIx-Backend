def get_params(params: dict, company=None) -> dict:
    """
    Payment va Company modeliga mos payme params tozalash funksiyasi.
    
    :param params: dict -> payme request parametrlari
    :param company: Company modeli -> order_id olish uchun
    :return: dict -> tozalangan parametrlar
    """
    account: dict = params.get("account")

    clean_params: dict = {}
    clean_params["_id"] = params.get("id")
    clean_params["time"] = params.get("time")
    clean_params["amount"] = params.get("amount")
    clean_params["reason"] = params.get("reason")

    if params.get("reason") is not None:
        clean_params["reason"] = params.get("reason")

    if account is not None:
        # Agar company berilgan bo'lsa, payme_account kompaniya modeldan olinadi
        if company and hasattr(company, 'payme_id'):
            account_name: str = company.payme_id
        else:
            from django.conf import settings
            account_name: str = settings.PAYME.get("PAYME_ACCOUNT", "order_id")
        clean_params["order_id"] = account.get(account_name)

    return clean_params
