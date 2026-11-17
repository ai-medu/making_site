from django.urls import path
from . import views

urlpatterns = [
    path('guides/', views.guide_list, name='robot_guide_list'),
    path('guides/new/', views.guide_create, name='robot_guide_create'),
    path('guides/<int:pk>/edit/', views.guide_update, name='robot_guide_update'),
    path('guides/<int:pk>/delete/', views.guide_delete, name='robot_guide_delete'),
    path('', views.levelup_institution_list, name='levelup_institution_list'),
    path('<int:institution_id>/', views.levelup_by_institution, name='robot_levelup_by_institution'),
    path('<int:institution_id>/add/', views.levelup_create, name='robot_levelup_create'),
    path('edit/<int:pk>/', views.robot_levelup_update, name='robot_levelup_update'),
    path('delete/<int:pk>/', views.robot_levelup_delete, name='robot_levelup_delete'),
    path('toggle/<int:pk>/<str:field>/', views.toggle_status, name='toggle_status'),
    path('dashboard/', views.levelup_dashboard, name='levelup_dashboard'),
    path('<int:institution_id>/release_auto/<str:year_month>/',views.auto_release_from_levelup,name='auto_release_from_levelup'),
    path('<int:institution_id>/release_preview/<str:year_month>/',views.release_preview,name='release_preview'),
    path('<int:institution_id>/release_confirm/<str:year_month>/',views.release_confirm,name='release_confirm'),
    path('toggle_shipped/<int:pk>/', views.toggle_shipped_student, name='toggle_shipped_student'),
]
