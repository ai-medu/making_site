from django.urls import path
from . import views

urlpatterns = [
    path('', views.resource_list, name='resource_list'),
    # ✅ 연간계획서 (PDF) - '<str:category>/' 보다 앞에 둠
    path('plans/', views.plan_list, name='plan_list'),
    path('plans/new/', views.plan_create, name='plan_create'),
    path('plans/<int:pk>/', views.plan_detail, name='plan_detail'),
    path('plans/<int:pk>/file/', views.plan_file, name='plan_file'),
    path('plans/<int:pk>/delete/', views.plan_delete, name='plan_delete'),

    path('<str:category>/', views.resource_detail, name='resource_detail'),
    
    # ✅ 로봇 하위 페이지
    path('robot/olloai/', views.robot_olloai, name='robot_olloai'),
    path('robot/probo/', views.robot_probo, name='robot_probo'),
    path('robot/xrobo/', views.robot_xrobo, name='robot_xrobo'),
    path('robot/jrobo/', views.robot_jrobo, name='robot_jrobo'),
]
