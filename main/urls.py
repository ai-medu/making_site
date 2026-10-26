from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),  # 홈페이지 URL
    path('making/', views.making_page, name='making_page'),
    path('menu-management/', views.menu_management, name='menu_management'),
    path('ai-manage/', views.ai_manage, name='ai_manage'),
    path('ai-manage/new/', views.ai_key_form, name='ai_key_create'),
    path('ai-manage/<int:pk>/edit/', views.ai_key_form, name='ai_key_edit'),
    path('ai-manage/<int:pk>/delete/', views.ai_key_delete, name='ai_key_delete'),
    path('ai-manage/<int:pk>/toggle/', views.ai_key_toggle, name='ai_key_toggle'),
    path('ai-manage/<int:pk>/test/', views.ai_key_test, name='ai_key_test'),
]
