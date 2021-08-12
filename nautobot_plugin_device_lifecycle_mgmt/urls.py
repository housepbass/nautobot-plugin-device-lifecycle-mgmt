"""Django urlpatterns declaration for nautobot_plugin_device_lifecycle_mgmt plugin."""
from django.urls import path
from nautobot.extras.views import ObjectChangeLogView
from nautobot_plugin_device_lifecycle_mgmt import views
from nautobot_plugin_device_lifecycle_mgmt.models import EoxNotice, SoftwareLCM, ValidatedSoftwareLCM


app_name = "nautobot_plugin_device_lifecycle_mgmt"

urlpatterns = [
    path("eox-notice/", views.EoxNoticesListView.as_view(), name="eoxnotice_list"),
    path("eox-notice/<uuid:pk>/", views.EoxNoticeView.as_view(), name="eoxnotice"),
    path("eox-notice/add/", views.EoxNoticeCreateView.as_view(), name="eoxnotice_add"),
    path("eox-notice/delete/", views.EoxNoticeBulkDeleteView.as_view(), name="eoxnotice_bulk_delete"),
    path("eox-notice/edit/", views.EoxNoticeBulkEditView.as_view(), name="eoxnotice_bulk_edit"),
    path("eox-notice/<uuid:pk>/delete/", views.EoxNoticeDeleteView.as_view(), name="eoxnotice_delete"),
    path("eox-notice/<uuid:pk>/edit/", views.EoxNoticeEditView.as_view(), name="eoxnotice_edit"),
    path(
        "eox-notice/<uuid:pk>/changelog/",
        ObjectChangeLogView.as_view(),
        name="eoxnotice_changelog",
        kwargs={"model": EoxNotice},
    ),
    path("eox-notice/import/", views.EoxNoticeBulkImportView.as_view(), name="eoxnotice_import"),
    # SoftwareLCM
    path("software/", views.SoftwareLCMListView.as_view(), name="softwarelcm_list"),
    path("software/<uuid:pk>/", views.SoftwareLCMView.as_view(), name="softwarelcm"),
    path("software/add/", views.SoftwareLCMCreateView.as_view(), name="softwarelcm_add"),
    path("software/<uuid:pk>/delete/", views.SoftwareLCMDeleteView.as_view(), name="softwarelcm_delete"),
    path("software/<uuid:pk>/edit/", views.SoftwareLCMEditView.as_view(), name="softwarelcm_edit"),
    path(
        "software/<uuid:pk>/changelog/",
        ObjectChangeLogView.as_view(),
        name="softwarelcm_changelog",
        kwargs={"model": SoftwareLCM},
    ),
    # ValidateSoftware
    path("validated-software/", views.ValidatedSoftwareLCMListView.as_view(), name="validatedsoftwarelcm_list"),
    path("validated-software/<uuid:pk>/", views.ValidatedSoftwareLCMView.as_view(), name="validatedsoftwarelcm"),
    path("validated-software/add/", views.ValidatedSoftwareLCMEditView.as_view(), name="validatedsoftwarelcm_add"),
    path(
        "validated-software/<uuid:pk>/delete/",
        views.ValidatedSoftwareLCMDeleteView.as_view(),
        name="validatedsoftwarelcm_delete",
    ),
    path(
        "validated-software/<uuid:pk>/edit/",
        views.ValidatedSoftwareLCMEditView.as_view(),
        name="validatedsoftwarelcm_edit",
    ),
    path(
        "validated-software/<uuid:pk>/changelog/",
        ObjectChangeLogView.as_view(),
        name="validatedsoftwarelcm_changelog",
        kwargs={"model": ValidatedSoftwareLCM},
    ),
]
