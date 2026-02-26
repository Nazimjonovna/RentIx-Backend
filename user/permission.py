from rest_framework.permissions import BasePermission
from datetime import date
from .models import CompanySubscription

class HasActiveSubscription(BasePermission):
    message = "Uzr, siz oylik subscriptionni to'lamagansiz."

    def has_permission(self, request, view):
        user = request.user
        if not user.is_authenticated:
            return False
        # Foydalanuvchi admin yoki manager bo'lishi kerak
        if user.role not in ["admin", "manager"]:
            self.message = "Sizda bunday ruxsat yo'q"
            return False
        # Kompaniyaning aktiv subscriptionini tekshirish
        company = None
        if user.role == "admin":
            company = getattr(user, "company", None)  # Adminning kompaniyasi
        elif user.role == "manager":
            company = getattr(user, "manager_company", None)  # Manager kompaniyasi (ForeignKey)
        if not company:
            self.message = "Kompaniya topilmadi"
            return False
        subscription = CompanySubscription.objects.filter(
            company=company,
            is_active=True,
            start_date__lte=date.today(),
            end_date__gte=date.today()
        ).first()
        if not subscription:
            self.message = "Uzr, siz oylik subscriptionni to'lamagansiz."
            return False
        return True


class IsCashbackOwner(BasePermission):
    message = "Siz faqat o‘zingizga tegishli cashback ma’lumotlarini ko‘ra olasiz."
    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        return obj.user == user
