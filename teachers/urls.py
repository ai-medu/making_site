# teachers/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('institutions/', views.institution_list, name='institution_list'),
    path('institutions/add/', views.add_institution, name='add_institution'),
    path('institutions/<int:pk>/edit/', views.institution_update, name='institution_update'),  # ✅ 수정
    path('institutions/<int:pk>/delete/', views.institution_delete, name='institution_delete'),
    path('institutions/<int:pk>/close/', views.institution_close, name='institution_close'),
    path('dashboard/', views.teacher_dashboard, name='teacher_dashboard'),
    path('nuribom-hub/', views.nuribom_hub, name='nuribom_hub'),
    path('nuribom-hub/save/', views.nuribom_save, name='nuribom_save'),
    path('nuribom-hub/load/', views.nuribom_load, name='nuribom_load'),
    path('nuribom-hub/generate/', views.nuribom_generate, name='nuribom_generate'),
    path('nuribom-hub/ai-section/', views.nuribom_ai_section, name='nuribom_ai_section'),

    path('extract-document/<str:kind>/', views.extract_document, name='extract_document'),
    path('bulk-create/<str:kind>/', views.bulk_create_documents, name='bulk_create_documents'),
    path('proof/<str:kind>/<int:pk>/', views.proof_file, name='proof_file'),
    path('proof/<str:kind>/<int:pk>/upload/', views.proof_upload, name='proof_upload'),
    path('proof/<str:kind>/<int:pk>/delete/', views.proof_delete, name='proof_delete'),

    path('educations/', views.education_list, name='education_list'),
    path('educations/new/', views.education_create, name='education_create'),
    path('education/<int:pk>/edit/', views.education_update, name='education_update'),
    path('education/<int:pk>/delete/', views.education_delete, name='education_delete'),
    
    path('certificates/', views.certificate_list, name='certificate_list'),
    path('certificate-catalog/', views.certificate_catalog, name='certificate_catalog'),
    path('certificate-catalog/acquire/', views.certificate_catalog_acquire, name='certificate_catalog_acquire'),
    path('certificate-catalog/save/', views.certificate_catalog_save, name='certificate_catalog_save'),
    path('certificate-catalog/<int:item_id>/delete/', views.certificate_catalog_delete, name='certificate_catalog_delete'),
    path('certificates/new/', views.certificate_create, name='certificate_create'),
    path("certificate/<int:pk>/edit/", views.certificate_update, name="certificate_update"),
    path("certificate/<int:pk>/delete/", views.certificate_delete, name="certificate_delete"),

    path('careers/', views.career_list, name='career_list'),
    path('careers/new/', views.career_create, name='career_create'),
    path("career/<int:pk>/edit/", views.career_update, name="career_update"),
    path("career/<int:pk>/delete/", views.career_delete, name="career_delete"),
    
    path('<int:teacher_id>/careers/', views.teacher_career_list, name='teacher_career_list'),
    path('<int:teacher_id>/certificates/', views.teacher_certificate_list, name='teacher_certificate_list'),
    
]
