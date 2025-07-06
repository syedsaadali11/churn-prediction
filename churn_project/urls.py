from django.contrib import admin
from django.urls import path, include    # you no longer need the view imports

urlpatterns = [
    path("", include("churn.urls")),     # whole churn app mounted at root
    path("admin/", admin.site.urls),
]
