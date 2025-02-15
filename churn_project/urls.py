from django.contrib import admin
from django.urls import path, include
from churn.views import landing_page, signup_view, login_view, logout_view

urlpatterns = [
    path('', landing_page, name='landing_page'),  # Landing Page (Initial)
    path('app/', include('churn.urls')),  # All other app pages
    path('admin/', admin.site.urls),  # Admin Panel
    
    # 🔥 Authentication Routes
    path('login/', login_view, name='login'),
    path('signup/', signup_view, name='signup'),
    path('logout/', logout_view, name='logout'),
]
