import logging

logger = logging.getLogger('django')


def logged(logged_message: str, logged_type: str = "debug") -> None:
    """
    Logging helper function for Payment and Payme transactions.
    
    :param logged_message: str -> log xabari
    :param logged_type: str -> log turi ("info", "warning", "error", "debug", "critical")
    """
    logged_type = logged_type.lower()

    if logged_type == 'info':
        logger.info(logged_message)
    elif logged_type == "warning":
        logger.warning(logged_message)
    elif logged_type == "error":
        logger.error(logged_message)
    elif logged_type == "debug":
        logger.debug(logged_message)
    elif logged_type == "critical":
        logger.critical(logged_message)
    else:
        # Default debug
        logger.debug(logged_message)
