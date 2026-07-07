from django.urls import path,include
from . import views

urlpatterns=[
    path('home',views.home, name='home'),
    path('login/',views.user_login, name='login'),
    path('register/', views.register, name='register'),
    path('logout/',views.user_logout, name='logout')
]