from django.urls import path

from . import views

app_name = "editor"

urlpatterns = [
    path("", views.editor_workspace, name="workspace"),
    path("preview/", views.live_preview, name="preview"),
    path("pdf/", views.generate_pdf, name="pdf"),
]
