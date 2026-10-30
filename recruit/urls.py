from django.urls import path
from . import views, dispatch_views

urlpatterns = [
    path("", views.recruit_list, name="recruit_list"),
    path("add/", views.recruit_add, name="recruit_add"),
    path("<int:pk>/edit/", views.recruit_edit, name="recruit_edit"),
    path("<int:pk>/delete/", views.recruit_delete, name="recruit_delete"),

    # ⭐ 복사
    path("<int:pk>/copy/", views.recruit_copy, name="recruit_copy"),

    # 출강 강사 모집
    path("dispatch/", dispatch_views.dispatch_list, name="dispatch_list"),
    path("dispatch/add/", dispatch_views.dispatch_add, name="dispatch_add"),
    path("dispatch/<int:pk>/edit/", dispatch_views.dispatch_edit, name="dispatch_edit"),
    path("dispatch/<int:pk>/delete/", dispatch_views.dispatch_delete, name="dispatch_delete"),
    path("dispatch/<int:pk>/toggle/", dispatch_views.dispatch_toggle, name="dispatch_toggle"),
    path("dispatch/<int:pk>/apply/", dispatch_views.dispatch_apply, name="dispatch_apply"),
    path("dispatch/<int:pk>/apply/cancel/", dispatch_views.dispatch_apply_cancel, name="dispatch_apply_cancel"),
    path("dispatch/applications/", dispatch_views.dispatch_applications, name="dispatch_applications"),
    path("dispatch/applications/<int:pk>/action/", dispatch_views.dispatch_application_action, name="dispatch_application_action"),

    path("timetable/", views.recruit_timetable, name="recruit_timetable"),

    # 지도사과정 과정 유형 관리
    path("instructor/courses/", views.instructor_course_list, name="instructor_course_list"),
    path("instructor/courses/add/", views.instructor_course_add, name="instructor_course_add"),
    path("instructor/courses/<int:pk>/edit/", views.instructor_course_edit, name="instructor_course_edit"),
    path("instructor/courses/<int:pk>/delete/", views.instructor_course_delete, name="instructor_course_delete"),
    path("instructor/courses/<int:pk>/api/", views.course_type_api, name="course_type_api"),
    path("instructor/cert-item/<int:pk>/api/", views.cert_item_api, name="cert_item_api"),

    # 지도사과정 모집 공고 관리
    path("instructor/", views.instructor_recruit, name="instructor_recruit"),
    path("instructor/add/", views.instructor_recruit_add, name="instructor_recruit_add"),
    path("instructor/<int:pk>/edit/", views.instructor_recruit_edit, name="instructor_recruit_edit"),
    path("instructor/<int:pk>/delete/", views.instructor_recruit_delete, name="instructor_recruit_delete"),
    path("instructor/<int:pk>/apply/", views.instructor_recruit_apply, name="instructor_recruit_apply"),
    path("instructor/<int:pk>/applications/", views.instructor_recruit_applications, name="instructor_recruit_applications"),
]
