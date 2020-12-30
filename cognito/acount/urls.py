from django.urls import re_path
from rest_framework import routers
from .views import LoginAPIView, SignUpAPIView, NotLoginRequiredAPIView, LoginRequiredAPIView

urlpatterns = [
    re_path(r'^signup/$', SignUpAPIView.as_view()),
    re_path(r'^login/$', LoginAPIView.as_view()),
    re_path(r'^notlogin/$', NotLoginRequiredAPIView.as_view()),
    re_path(r'^needlogin/$', LoginRequiredAPIView.as_view()),

]