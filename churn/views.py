import os
import json
import pickle
import pandas as pd
from catboost import CatBoostClassifier
from django.shortcuts import render, redirect
from django.conf import settings
from django.core.files.storage import default_storage
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages

# ── Load Models & Artifacts ───────────────────────────────────────
BASE_MODEL_DIR = os.path.join(settings.BASE_DIR, "churn", "models")

cat_model_path     = os.path.join(BASE_MODEL_DIR, "catboost_model.cbm")
lgb_model_path     = os.path.join(BASE_MODEL_DIR, "lgb_model.pkl")
xgb_model_path     = os.path.join(BASE_MODEL_DIR, "xgb_model.pkl")
threshold_path     = os.path.join(BASE_MODEL_DIR, "best_threshold.txt")
cat_cols_path      = os.path.join(BASE_MODEL_DIR, "cat_columns.json")
onehot_cols_path   = os.path.join(BASE_MODEL_DIR, "onehot_columns.json")

cat_model = CatBoostClassifier()
cat_model.load_model(cat_model_path)

with open(lgb_model_path, "rb") as f:
    lgb_model = pickle.load(f)

with open(xgb_model_path, "rb") as f:
    xgb_model = pickle.load(f)

with open(threshold_path, "r") as f:
    best_threshold = float(f.read())

with open(cat_cols_path, "r") as f:
    cat_cols = json.load(f)

with open(onehot_cols_path, "r") as f:
    onehot_cols = json.load(f)

# ── Suggestion Engine ─────────────────────────────────────────────
def analyze_churn_factors(input_data):
    reasons = []
    suggestions = []

    if input_data["MonthlyCharges"] > 75:
        reasons.append("High monthly charges may be discouraging customers.")
        suggestions.append("Consider offering discounts or loyalty programs.")

    if input_data["tenure"] < 12:
        reasons.append("Customers with short tenure are more likely to churn.")
        suggestions.append("Improve onboarding experience and engagement.")

    if input_data.get("Contract_Month-to-month", 0) == 1:
        reasons.append("Month-to-month contracts have a higher churn rate.")
        suggestions.append("Promote longer-term plans with incentives.")

    if input_data.get("TechSupport_No", 0) == 1:
        reasons.append("Lack of tech support can reduce customer satisfaction.")
        suggestions.append("Offer better support plans or free trials.")

    if input_data.get("PaymentMethod_Electronic check", 0) == 1:
        reasons.append("Electronic check users churn more often.")
        suggestions.append("Encourage switching to credit card or bank transfer.")

    return reasons, suggestions

# ── Views ─────────────────────────────────────────────────────────
@login_required
def dashboard(request):
    return render(request, 'dashboard.html')

@login_required
def profile(request):
    return render(request, 'profile.html')

@login_required
def admin_dashboard(request):
    return render(request, "admin_dashboard.html")

def about(request): return render(request, 'about.html')
def services(request): return render(request, 'services.html')
def faq(request): return render(request, 'faq.html')
def contact(request): return render(request, 'contact.html')
def terms(request): return render(request, 'terms.html')

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

@login_required
def predict_churn(request):
    result = None
    if request.method == "POST":
        try:
            # Step 1: Build customer input record
            record = {
                "gender": request.POST.get("gender"),
                "SeniorCitizen": int(request.POST.get("senior_citizen")),
                "Partner": request.POST.get("partner"),
                "Dependents": request.POST.get("dependents"),
                "tenure": int(request.POST.get("tenure")),
                "PhoneService": request.POST.get("phone_service"),
                "MultipleLines": request.POST.get("multiple_lines"),
                "InternetService": request.POST.get("internet_service"),
                "OnlineSecurity": request.POST.get("online_security"),
                "OnlineBackup": request.POST.get("online_backup"),
                "DeviceProtection": request.POST.get("device_protection"),
                "TechSupport": request.POST.get("tech_support"),
                "StreamingTV": request.POST.get("streaming_tv"),
                "StreamingMovies": request.POST.get("streaming_movies"),
                "Contract": request.POST.get("contract"),
                "PaperlessBilling": request.POST.get("paperless_billing"),
                "PaymentMethod": request.POST.get("payment_method"),
                "MonthlyCharges": float(request.POST.get("monthly_charges")),
                "TotalCharges": float(request.POST.get("total_charges")),
            }

            # Step 2: Convert to DataFrame
            df = pd.DataFrame([record])

            # Step 3: CatBoost preprocessing
            for col in cat_cols:
                df[col] = df[col].astype(str)

            # Step 4: CatBoost prediction
            p_cat = cat_model.predict_proba(df)[0][1]

            # Step 5: One-hot encode for LGB/XGB
            df_oh = pd.get_dummies(df)
            df_oh = df_oh.reindex(columns=onehot_cols, fill_value=0)

            # Step 6: LGB/XGB predictions
            p_lgb = lgb_model.predict_proba(df_oh)[0][1]
            p_xgb = xgb_model.predict_proba(df_oh)[0][1]

            # Step 7: Ensemble & decision
            final_prob = (p_cat + p_lgb + p_xgb) / 3
            decision = "Likely to Churn" if final_prob > best_threshold else "Not Likely to Churn"

            # Step 8: Suggestion engine
            enriched_input = {**record, **df_oh.iloc[0].to_dict()}
            reasons, suggestions = analyze_churn_factors(enriched_input)

            result = {
                "churn_probability": round(final_prob, 2),
                "churn_decision": decision,
                "reason": reasons,
                "suggestions": suggestions
            }

        except Exception as e:
            messages.error(request, f"Prediction error: {e}")

    return render(request, "predict.html", {"result": result})

@login_required
def batch_predict(request):
    csv_results = []

    if request.method == "POST" and request.FILES.get("csv_file"):
        csv_file = request.FILES["csv_file"]

        try:
            df = pd.read_csv(csv_file)

            # Just check if required fields exist exactly as expected
            required_fields = ["tenure", "MonthlyCharges", "TotalCharges"]
            for field in required_fields:
                if field not in df.columns:
                    messages.error(request, f"Missing required field: {field}")
                    return render(request, "batch_predict.html", {"csv_results": None})

            # Ensure categorical columns are str
            for col in cat_cols:
                if col in df.columns:
                    df[col] = df[col].astype(str)

            df_oh = pd.get_dummies(df).reindex(columns=onehot_cols, fill_value=0)

            cat_probs = cat_model.predict_proba(df)[:, 1]
            lgb_probs = lgb_model.predict_proba(df_oh)[:, 1]
            xgb_probs = xgb_model.predict_proba(df_oh)[:, 1]

            final_probs = (cat_probs + lgb_probs + xgb_probs) / 3
            predictions = ["Likely to Churn" if p > best_threshold else "Not Likely to Churn" for p in final_probs]

            for i, row in df.iterrows():
                enriched_input = {**row.to_dict(), **df_oh.iloc[i].to_dict()}
                reasons, suggestions = analyze_churn_factors(enriched_input)

                csv_results.append({
                    "tenure": row.get("tenure"),
                    "MonthlyCharges": row.get("MonthlyCharges"),
                    "TotalCharges": row.get("TotalCharges"),
                    "Churn_Probability": round(final_probs[i] * 100, 1),
                    "Churn_Decision": predictions[i],
                    "reasons": reasons,
                    "suggestions": suggestions
                })

        except Exception as e:
            messages.error(request, f"Error processing CSV: {str(e)}")
            return render(request, "batch_predict.html", {"csv_results": None})

    return render(request, "batch_predict.html", {"csv_results": csv_results})

# ── Root / Home / Login ───────────────────────────────────────────
def landing_page(request):
    if request.user.is_authenticated:
        return redirect('home')
    return render(request, 'landing_page.html')

def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            if user.is_superuser:
                return redirect('admin_dashboard')
            next_url = request.GET.get("next") or request.POST.get("next")
            return redirect(next_url or "home")
        messages.error(request, "Invalid username or password.")
    return render(request, "login.html", {"next": request.GET.get("next", "")})

def home_view(request):
    if not request.user.is_authenticated:
        return redirect('login')
    return render(request, "home.html")
