ORDER_NOT_FOUND = -31050
TRANSACTION_NOT_FOUND = -31003
UNABLE_TO_PERFORM_OPERATION = -31008
INVALID_AMOUNT = -31001
ON_PROCESS = -31099
ORDER_FOUND = 200

CREATE_TRANSACTION = 1
CLOSE_TRANSACTION = 2
CANCEL_TRANSACTION_CODE = -1
PERFORM_CANCELED_CODE = -2
ORDER_NOT_FOUND_MESSAGE = {
    "uz": "Buyurtma topilmadi",
    "ru": "Заказ не найден",
    "en": "Order not fond"
}
TRANSACTION_NOT_FOUND_MESSAGE = {
    "uz": "Tranzaksiya topilmadi",
    "ru": "Транзакция не найдена",
    "en": "Transaction not found"
}
UNABLE_TO_PERFORM_OPERATION_MESSAGE = {
    "uz": "Ushbu amalni bajarib bo'lmaydi",
    "ru": "Невозможно выполнить данную операцию",
    "en": "Unable to perform operation"
}
INVALID_AMOUNT_MESSAGE = {
    "uz": "Miqdori notog'ri",
    "ru": "Неверная сумма",
    "en": "Invalid amount"
}

AUTH_ERROR = {
    "error": {
        "code": -32504,
        "message": {
            "ru": "пользователь не существует",
            "uz": "foydalanuvchi mavjud emas",
            "en": "user does not exist"
        },
        "data": "user does not exist"
    }
}

INVALID_AMOUNT = -2
INVALID_ACTION = -4
TRANSACTION_NOT_FOUND = -6
ORDER_NOT_FOUND = -5
PREPARE = '0'
COMPLETE = '1'
A_LACK_OF_MONEY = '-5017'
A_LACK_OF_MONEY_CODE = -9
AUTHORIZATION_FAIL = 'AUTHORIZATION_FAIL'
AUTHORIZATION_FAIL_CODE = -1
ORDER_FOUND = True