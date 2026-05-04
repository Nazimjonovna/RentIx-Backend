from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from .views import (
    # Auth & Registration
    CarRateDetailView, CarRateListCreateView, CheckInOutViewSet, PhoneView, CodeView, ValidatedcodeView, RegisterView,
    GoogleRegisterView, GoogleCallbackView,GetUserTokenView,

    # User
    UserProfilView,BlockUserView,UsersAllGetView,

    # Order
    OrderPageView, OrderCreateView, GetOwnAllOrderView, OrderChangeView,
    OrderStatusView,GetCompanyAllOrderView, 

    # Car
    CarCreateView, AvailableCarsAPIView, GetAllCarView, CarCRUDView,
    AvailableCarModelFilterView, CarCostFilterAPIView,DiscountView,
    GetAllCarView,CarImageAPIView,CarImageByCarAPIView,ViloyatlarViewSet,
    GetCarModelView,GenerateUploadURL,CarImageDeleteAPIView,

    # Admin & Manager
    CreateAdminView, CompanyWorkDayCRUDView, CreateManagerView, ManagerCRUDView,
    LoginView, GetAllManagerView,FilialView, FilialDetailView,AdminCRUDView,
    CompanyWorkView,GetFilialWorkdays,GetCompaniView, 

    # Rate
    CreateRateView,

    # Chat & Notifications
    ChatViewSet, ChatMessageViewSet, NotificationViewSet,

    #Payment
    MerchantAPIView, ClickUzMerchantAPIView,

    # Company Subscription
    CompanySubscriptionAPIView,

    # Bot Notification
    BotNotificationViewSet,MeView, CarBrandListView, CarModelListView,
)

# Router for ViewSets
router = DefaultRouter()
router.register(r'chats', ChatViewSet, basename='chat')
router.register(r'messages', ChatMessageViewSet, basename='chat-message')
router.register(r'notifications', NotificationViewSet, basename='notification')
router.register(r'bot-notifications', BotNotificationViewSet, basename='bot-notifications')
router.register("checkings", CheckInOutViewSet, basename="checkings")


urlpatterns = [
    # 🔹 Registration & Auth
    path('phone/', PhoneView.as_view(), name='phone'),
    path('code/', CodeView.as_view(), name='code'),
    path('validatedcode/', ValidatedcodeView.as_view(), name='validatedcode'),
    path("user-register/", RegisterView.as_view(), name="register-user"),
    path('token/', GetUserTokenView.as_view(), name = "get-token"),

    # 🔹 User profile
    path("user-profile/<int:pk>/", UserProfilView.as_view(), name="user-profile"),
    path("block-user/", BlockUserView.as_view(), name="block-user"),
    path("all-users/", UsersAllGetView.as_view(), name="all-users"),

    # 🔹 Orders
    path("orderpage/", OrderPageView.as_view(), name="orderpage"),
    path("create-order/", OrderCreateView.as_view(), name="create-order"),
    path("orders/get/user/<int:pk>/", GetOwnAllOrderView.as_view(), name="user-orders"),
    path("order/<int:pk>/", OrderChangeView.as_view(), name="order-detail"),
    path("order-status/", OrderStatusView.as_view(), name="order-status"),
    path("get/order/company/<int:pk>/", GetCompanyAllOrderView.as_view()),

    # 🔹 Cars
    path("create-car/", CarCreateView.as_view(), name="create-car"),
    path("cars/", GetAllCarView.as_view(), name="get-all-cars"),
    path("car/<int:pk>/", CarCRUDView.as_view(), name="car-crud"),
    path("filter-car/", AvailableCarsAPIView.as_view(), name="filter-car"),
    path("rates/", CarRateListCreateView.as_view(), name="car-rate-list-create"),
    path("rates/<int:pk>/", CarRateDetailView.as_view(), name="car-rate-detail"),
    path("filter-car-model/", AvailableCarModelFilterView.as_view(), name="filter-car-model"),
    path("filter-car-cost/", CarCostFilterAPIView.as_view(), name="filter-car-cost"),
    path("discount/", DiscountView.as_view(), name="discount"),
    path("car-images/", CarImageAPIView.as_view(), name="car-images"),
    path("car-images/<int:pk>/", CarImageByCarAPIView.as_view(), name="car-image-detail"),
    path("viloyatlar/", ViloyatlarViewSet.as_view({'get': 'list', 'post': 'create'}), name="viloyatlar"),
    path("viloyatlar/<int:pk>/", ViloyatlarViewSet.as_view({'get': 'retrieve', 'put': 'update', 'delete': 'destroy'}), name="viloyat-detail"),
    path("get/model/portfolio/cars/", GetCarModelView.as_view()),
    path('generate-upload-url/', GenerateUploadURL.as_view(), name='generate-upload-url'),
    path("car-images/<int:pk>/delete/", CarImageDeleteAPIView.as_view()),

    # 🔹 Admin & Manager
    path("companies/", CreateAdminView.as_view(), name="create-admin"), 
    path("companies/<int:pk>/", AdminCRUDView.as_view(), name="create-admin"), 
    path("companies/<int:company_id>/workdays/", CompanyWorkView.as_view(), name="admin-crud"),  # list, create
    path("workdays/<int:pk>/", CompanyWorkDayCRUDView.as_view(), name="admin-crud"),
    path("workdays/get/filial/<int:pk>/", GetFilialWorkdays.as_view()),
    path('create-manager/', CreateManagerView.as_view(), name="create-manager"),
    path('manager-crud/<int:pk>/', ManagerCRUDView.as_view(), name="manager-crud"),
    path("login/", LoginView.as_view(), name="login"),
    path("managers/", GetAllManagerView.as_view(), name="all-managers"),
    path("filials/", FilialView.as_view(), name="filials"),
    path("filials/<int:pk>/", FilialDetailView.as_view(), name="filial-detail"),
    path('company/get-id/', GetCompaniView.as_view()),

    # 🔹 Google OAuth
    path('api/auth/google/start/', GoogleRegisterView.as_view(), name='google-start'),
    path('api/auth/google/callback/', GoogleCallbackView.as_view(), name='google-callback'),

    # 🔹 Ratings
    path("rate/", CreateRateView.as_view(), name="create-rate"),

    # 🔹 Include router endpoints (Chat, Message, Notification)
    path('', include(router.urls)),

    # Token endpoints
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # 🔹 Payment
    path("merchant/", MerchantAPIView.as_view(), name="merchant"),
    path('click/', ClickUzMerchantAPIView.as_view()),
    
    path("auth/me/", MeView.as_view(), name="auth-me"),
    path("car-brands/", CarBrandListView.as_view()),
    path("car-models/", CarModelListView.as_view()),

    # # 🔹 Company Subscriptions
    # path('company/subscriptions/', CompanySubscriptionAPIView.as_view(), name='company-subscriptions'),
    # path('company/subscriptions/<int:pk>/', CompanySubscriptionAPIView.as_view(), name='company-subscription-detail'),

]
#// db must apdate