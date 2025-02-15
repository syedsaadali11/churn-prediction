import os
import pandas as pd
import pickle
from django.shortcuts import render, redirect
from django.conf import settings
from django.core.files.storage import default_storage
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages

# Load Model and Scaler Dynamically
BASE_DIR = settings.BASE_DIR
MODEL_PATH = os.path.join(BASE_DIR, "churn", "models", r"D:\customer\churn_project\churn\models\xgboost_churn_model.pkl")
SCALER_PATH = os.path.join(BASE_DIR, "churn", "models", r"D:\customer\churn_project\churn\models\scaler.pkl")

# Load ML Model and Scaler
try:
    with open(MODEL_PATH, "rb") as file:
        model = pickle.load(file)

    with open(SCALER_PATH, "rb") as file:
        scaler = pickle.load(file)
except FileNotFoundError:
    model, scaler = None, None

# Feature columns used in the model
FEATURE_COLUMNS = [
    'tenure', 'MonthlyCharges', 'TotalCharges', 'gender_Male', 'SeniorCitizen_1',
    'Partner_Yes', 'Dependents_Yes', 'PhoneService_Yes', 'MultipleLines_No phone service',
    'MultipleLines_Yes', 'InternetService_Fiber optic', 'InternetService_No',
    'OnlineSecurity_No internet service', 'OnlineSecurity_Yes', 'OnlineBackup_No internet service',
    'OnlineBackup_Yes', 'DeviceProtection_No internet service', 'DeviceProtection_Yes',
    'TechSupport_No internet service', 'TechSupport_Yes', 'StreamingTV_No internet service',
    'StreamingTV_Yes', 'StreamingMovies_No internet service', 'StreamingMovies_Yes',
    'Contract_One year', 'Contract_Two year', 'PaperlessBilling_Yes',
    'PaymentMethod_Credit card (automatic)', 'PaymentMethod_Electronic check', 'PaymentMethod_Mailed check'
]

# Function to determine churn reasons and suggestions
def analyze_churn_factors(input_data):
    reasons = []
    suggestions = []

    # High Monthly Charges
    if input_data["MonthlyCharges"] > 75:
        reasons.append("High monthly charges may be discouraging customers.")
        suggestions.append("Consider offering discounts or loyalty programs.")

    # Short Tenure
    if input_data["tenure"] < 12:
        reasons.append("Customers with short tenure are more likely to churn.")
        suggestions.append("Improve onboarding experience and engagement.")

    # No Contract
    if input_data.get("Contract_Month-to-month", 0) == 1:
        reasons.append("Customers with month-to-month contracts have a higher churn rate.")
        suggestions.append("Encourage customers to switch to long-term contracts with incentives.")

    # No Tech Support or Security
    if input_data.get("TechSupport_No", 0) == 1:
        reasons.append("Lack of technical support may lead to customer dissatisfaction.")
        suggestions.append("Offer better support plans or free trials.")

    # Electronic Check Payment
    if input_data.get("PaymentMethod_Electronic check", 0) == 1:
        reasons.append("Customers paying via electronic check have higher churn rates.")
        suggestions.append("Encourage auto-pay options like credit card or bank transfer.")

    return reasons, suggestions

# 🔹 Landing Page
def landing_page(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'landing_page.html')

# 🔹 Dashboard & Profile
@login_required
def dashboard(request):
    return render(request, 'dashboard.html')

@login_required
def profile(request):
    return render(request, 'profile.html')

@login_required
def admin_dashboard(request):
    return render(request, "admin_dashboard.html")

# 🔹 Static Pages
def about(request):
    return render(request, 'about.html')

def services(request):
    return render(request, 'services.html')

def faq(request):
    return render(request, 'faq.html')

def contact(request):
    return render(request, 'contact.html')

def terms(request):
    return render(request, 'terms.html')

# 🔹 Authentication Views
def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, "Login successful. Welcome back!")
            return redirect('dashboard')
        else:
            messages.error(request, "Invalid username or password.")

    return render(request, 'login.html')

def signup_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        password1 = request.POST.get("password1")
        password2 = request.POST.get("password2")

        if password1 != password2:
            messages.error(request, "Passwords do not match!")
            return redirect('signup')

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
            return redirect('signup')

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email is already registered.")
            return redirect('signup')

        user = User.objects.create_user(username=username, email=email, password=password1)
        user.save()
        messages.success(request, "Account created successfully! You can now log in.")
        return redirect('login')

    return render(request, 'signup.html')

def logout_view(request):
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect('landing_page')

# 🔹 Batch Prediction (CSV Upload)
@login_required
def batch_predict(request):
    csv_results = None
    if request.method == "POST" and "csv_file" in request.FILES:
        try:
            csv_file = request.FILES["csv_file"]
            file_path = default_storage.save("uploaded_data.csv", csv_file)
            df = pd.read_csv(file_path)

            if "Churn" in df.columns:
                df.drop(columns=["Churn"], inplace=True)

            missing_cols = set(FEATURE_COLUMNS) - set(df.columns)
            for col in missing_cols:
                df[col] = 0 

            df[['tenure', 'MonthlyCharges', 'TotalCharges']] = scaler.transform(
                df[['tenure', 'MonthlyCharges', 'TotalCharges']]
            )

            churn_probabilities = model.predict_proba(df)[:, 1]
            churn_decisions = ["Likely to Churn" if prob > 0.5 else "Not Likely to Churn" for prob in churn_probabilities]

            df["Churn_Probability"] = churn_probabilities.round(2)
            df["Churn_Decision"] = churn_decisions
            csv_results = df.to_dict(orient="records")

        except Exception as e:
            messages.error(request, f"Error processing CSV: {str(e)}")

    return render(request, "batch_predict.html", {"csv_results": csv_results})

# 🔹 Manual Churn Prediction
@login_required
def predict_churn(request):
    result = None
    if request.method == "POST":
        try:
            input_data = {col: 0 for col in FEATURE_COLUMNS}
            input_data["tenure"] = float(request.POST.get("tenure", 0))
            input_data["MonthlyCharges"] = float(request.POST.get("monthly_charges", 0))
            input_data["TotalCharges"] = float(request.POST.get("total_charges", 0))

            categorical_fields = [
                "gender", "senior_citizen", "partner", "dependents", "phone_service", 
                "multiple_lines", "internet_service", "online_security", "online_backup",
                "device_protection", "tech_support", "streaming_tv", "streaming_movies",
                "contract", "paperless_billing", "payment_method"
            ]

            for field in categorical_fields:
                selected_option = request.POST.get(field, "No")
                feature_name = f"{field}_{selected_option}"
                if feature_name in input_data:
                    input_data[feature_name] = 1

            df = pd.DataFrame([input_data])
            df[['tenure', 'MonthlyCharges', 'TotalCharges']] = scaler.transform(
                df[['tenure', 'MonthlyCharges', 'TotalCharges']]
            )

            churn_probability = model.predict_proba(df)[:, 1][0]
            churn_decision = "Likely to Churn" if churn_probability > 0.5 else "Not Likely to Churn"
            reasons, suggestions = analyze_churn_factors(input_data)

            result = {"churn_probability": round(churn_probability, 2), "churn_decision": churn_decision, "reason": reasons, "suggestions": suggestions}

        except Exception as e:
            messages.error(request, f"Prediction error: {str(e)}")

    return render(request, "predict.html", {"result": result})
