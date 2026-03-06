from django.urls import path
from apps.core.views import AttachmentDestroyView, AttachmentListCreateView

app_name = "core"

urlpatterns = [
    path("attachments/", AttachmentListCreateView.as_view(), name="attachment-list"),
    path("attachments/<int:pk>/", AttachmentDestroyView.as_view(), name="attachment-detail"),
]
