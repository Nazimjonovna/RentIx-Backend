from googletrans import Translator

translator = Translator()

class AutoTranslateMixin:
    """
    name -> name_ru, name_en auto translate
    """
    TRANSLATE_FIELDS = []  # ['name', 'title', ...]

    def auto_translate(self, instance):
        for field in self.TRANSLATE_FIELDS:
            value = getattr(instance, field, None)

            if value:
                try:
                    setattr(
                        instance,
                        f"{field}_ru",
                        translator.translate(value, src='uz', dest='ru').text
                    )
                    setattr(
                        instance,
                        f"{field}_en",
                        translator.translate(value, src='uz', dest='en').text
                    )
                except Exception:
                    pass
