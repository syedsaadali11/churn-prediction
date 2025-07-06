from django.urls import path
from .views import (
    landing_page, logout_view,          
    home_view,                  
    about, contact, services, faq, terms,
    predict_churn, batch_predict,
    login_view, signup_view,
    dashboard, profile, admin_dashboard
)

urlpatterns = [
    path("",  landing_page,  name="landing_page"),   # root
    path("home/", home_view, name="home"),           
    
    path("about/",          about,           name="about"),
    path("contact/",        contact,         name="contact"),
    path("services/",       services,        name="services"),
    path("faq/",            faq,             name="faq"),
    path("terms/",          terms,           name="terms"),

    path("predict/",        predict_churn,   name="predict"),
    path("batch-predict/",  batch_predict,   name="batch_predict"),

    path("login/",          login_view,      name="login"),
    path("signup/",         signup_view,     name="signup"),
    path("dashboard/",      dashboard,       name="dashboard"),
    path("profile/",        profile,         name="profile"),
    path("admin-dashboard/",admin_dashboard, name="admin_dashboard"),
    path("logout/", logout_view, name="logout"), 
]
