from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from User.models import User, Company  # sizning user modeli

class Command(BaseCommand):
    help = 'Create or update user for Payme transactions dynamically'

    def handle(self, *args, **options):
        try:
            # Company ma’lumotidan Payme params olish
            company = Company.objects.first()  # yoki kerakli company filter bilan tanlash
            if not company or not company.payme_id:
                self.stdout.write(self.style.ERROR('Company Payme ID or SECRET_KEY not set.'))
                return

            # Foydalanuvchi yaratish/yangilash
            username = f'payme_{company.id}'  # har company uchun unique username
            password = company.payme_id  # payme_id yoki secret key
            username_field = User.USERNAME_FIELD

            user, created = User.objects.update_or_create(
                **{username_field: username},
                defaults={'is_active': True}
            )
            user.set_password(password)
            user.save()

            if created:
                self.stdout.write(self.style.SUCCESS(f'Payme user "{username}" created successfully.'))
            else:
                self.stdout.write(self.style.SUCCESS(f'Payme user "{username}" updated successfully.'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}'))
