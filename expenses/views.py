from django.shortcuts import render, redirect, HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from .models import Category, Expense
from django.contrib import messages
from django.contrib.auth.models import User
from django.core.paginator import Paginator
import json
from django.http import JsonResponse
from userpreferences.models import UserPreference
import datetime
import requests
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from django.contrib.sessions.models import Session
from datetime import date
from sklearn.naive_bayes import MultinomialNB
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
import nltk
from django.conf import settings
from django.core.mail import send_mail
from .models import ExpenseLimit
from django.db.models import Sum 
from django.views.decorators.csrf import csrf_exempt

# ------------------------- MODEL TRAINING PART -------------------------
data = pd.read_csv('dataset.csv')
data = data.dropna()
data = data.drop_duplicates()
stop_words = set(stopwords.words('english'))

def rule_based_category(description):
    desc = description.lower()

    rules = {
        'food': ['pizza', 'burger', 'biryani', 'tea', 'coffee', 'zomato', 'swiggy', 'snack', 'vadapav', 'sandwich'],
        'transportation': ['uber', 'ola', 'auto', 'bus', 'train', 'metro', 'petrol', 'taxi'],
        'utilities': ['electricity', 'bill', 'recharge', 'wifi', 'internet', 'gas', 'light'],
        'shopping': ['amazon', 'flipkart', 'buy', 'purchase', 'order', 'clothes'],
        'entertainment': ['netflix', 'movie', 'spotify', 'game', 'youtube'],
        'health': ['doctor', 'hospital', 'medicine', 'clinic'],
        'education': ['fees', 'books','pen', 'book', 'course', 'college', 'school'],
        'electronics': ['headphone', 'earphone', 'earbuds', 'charger', 'laptop','mouse','keyboard', 'CPU', 'mobile', 'tv'],
        'furniture': ['sofa', 'bed', 'bench', 'chair', 'table', 'desk']
    }

    for category, keywords in rules.items():
        for word in keywords:
            if word in desc:
                return category

    return None

def preprocess_text(text):
    tokens = word_tokenize(text.lower())
    tokens = [t for t in tokens if t.isalnum() and t not in stop_words]
    return ' '.join(tokens)

data['clean_description'] = data['clean_description'].astype(str)
data['clean_description'] = data['clean_description'].apply(preprocess_text)

tfidf_vectorizer = TfidfVectorizer(ngram_range=(1,2))
X = tfidf_vectorizer.fit_transform(data['clean_description'])
model = MultinomialNB()
model.fit(X, data['category'])
# ----------------------------------------------------------------------

@login_required(login_url='/authentication/login')
def search_expenses(request):
    if request.method == 'POST':
        search_str = json.loads(request.body).get('searchText')
        expenses = Expense.objects.filter(
            amount__istartswith=search_str, owner=request.user) | Expense.objects.filter(
            date__istartswith=search_str, owner=request.user) | Expense.objects.filter(
            description__icontains=search_str, owner=request.user) | Expense.objects.filter(
            category__icontains=search_str, owner=request.user)
        data = expenses.values()
        return JsonResponse(list(data), safe=False)

@login_required(login_url='/authentication/login')
def index(request):
    categories = Category.objects.all()
    expenses = Expense.objects.filter(owner=request.user)

    sort_order = request.GET.get('sort')
    if sort_order == 'amount_asc':
        expenses = expenses.order_by('amount')
    elif sort_order == 'amount_desc':
        expenses = expenses.order_by('-amount')
    elif sort_order == 'date_asc':
        expenses = expenses.order_by('date')
    elif sort_order == 'date_desc':
        expenses = expenses.order_by('-date')

    paginator = Paginator(expenses, 5)
    page_number = request.GET.get('page')
    page_obj = Paginator.get_page(paginator, page_number)
    try:
        currency = UserPreference.objects.get(user=request.user).currency
    except:
        currency = None

    total = page_obj.paginator.num_pages
    context = {
        'expenses': expenses,
        'page_obj': page_obj,
        'currency': currency,
        'total': total,
        'sort_order': sort_order,
    }
    return render(request, 'expenses/index.html', context)

daily_expense_amounts = {}

@login_required(login_url='/authentication/login')
def add_expense(request):
    categories = Category.objects.all()
    context = {
        'categories': categories,
        'values': request.POST
    }
    if request.method == 'GET':
        return render(request, 'expenses/add_expense.html', context)

    if request.method == 'POST':
        amount = request.POST['amount']
        date_str = request.POST.get('expense_date')
        if not amount:
            messages.error(request, 'Amount is required')
            return render(request, 'expenses/add_expense.html', context)

        description = request.POST['description']
        date = request.POST['expense_date']
        # 🔥 Step 1: Rule-based
        predicted_category = rule_based_category(description)
         
        # 🔥 Step 2: ML fallback
        if not predicted_category:
            clean_desc = preprocess_text(description)
            vector = tfidf_vectorizer.transform([clean_desc])
            predicted_category = model.predict(vector)[0]

        # 🔥 Final safety
        if not predicted_category:
            predicted_category = 'others'

        if not description:
            messages.error(request, 'description is required')
            return render(request, 'expenses/add_expense.html', context)

        try:
            date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
            today = datetime.date.today()

            if date > today:
                messages.error(request, 'Date cannot be in the future')
                return render(request, 'expenses/add_expense.html', context)

            user = request.user
            expense_limits = ExpenseLimit.objects.filter(owner=user)
            if expense_limits.exists():
                daily_expense_limit = expense_limits.first().daily_expense_limit
            else:
                daily_expense_limit = 5000

            total_expenses_today = get_expense_of_day(user) + float(amount)
            if total_expenses_today > daily_expense_limit:
                subject = 'Daily Expense Limit Exceeded'
                message = f'Hello {user.username},\n\nYour expenses for today have exceeded your daily expense limit. Please review your expenses.'
                from_email = settings.EMAIL_HOST_USER
                to_email = [user.email]
                # send_mail(subject, message, from_email, to_email, fail_silently=False)
                messages.warning(request, 'Your expenses for today exceed your daily expense limit')

            Expense.objects.create(owner=request.user, amount=amount, date=date,
                                   category=predicted_category, description=description)
            messages.success(request, 'Expense saved successfully')
            return redirect('expenses')
        except ValueError:
            messages.error(request, 'Invalid date format')
            return render(request, 'expenses/add_expense.html', context)

@login_required(login_url='/authentication/login')
def expense_edit(request, id):
    expense = Expense.objects.get(pk=id)
    categories = Category.objects.all()
    context = {
        'expense': expense,
        'values': expense,
        'categories': categories
    }
    if request.method == 'GET':
        return render(request, 'expenses/edit-expense.html', context)
    if request.method == 'POST':
        amount = request.POST['amount']
        date_str = request.POST.get('expense_date')

        if not amount:
            messages.error(request, 'Amount is required')
            return render(request, 'expenses/edit-expense.html', context)
        description = request.POST['description']
        date = request.POST['expense_date']
        category = request.POST['category']

        if not description:
            messages.error(request, 'description is required')
            return render(request, 'expenses/edit-expense.html', context)

        try:
            date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
            today = datetime.date.today()

            if date > today:
                messages.error(request, 'Date cannot be in the future')
                return render(request, 'expenses/add_expense.html', context)

            expense.owner = request.user
            expense.amount = amount
            expense.date = date
            expense.category = category
            expense.description = description

            expense.save()
            messages.success(request, 'Expense saved successfully')
            return redirect('expenses')
        except ValueError:
            messages.error(request, 'Invalid date format')
            return render(request, 'expenses/edit_income.html', context)

@login_required(login_url='/authentication/login')
def delete_expense(request, id):
    expense = Expense.objects.get(pk=id)
    expense.delete()
    messages.success(request, 'Expense removed')
    return redirect('expenses')
@login_required(login_url='/authentication/login')
def expense_category_summary(request):
    todays_date = datetime.date.today()
    six_months_ago = todays_date - datetime.timedelta(days=30 * 6)
    expenses = Expense.objects.filter(owner=request.user,
                                      date__gte=six_months_ago, date__lte=todays_date)
    finalrep = {}

    def get_category(expense):
        return expense.category

    category_list = list(set(map(get_category, expenses)))

    def get_expense_category_amount(category):
        amount = 0
        filtered_by_category = expenses.filter(category=category)
        for item in filtered_by_category:
            amount += item.amount
        return amount

    for x in expenses:
        for y in category_list:
            finalrep[y] = get_expense_category_amount(y)

    # ✅ Weekly summary added
    seven_days_ago = todays_date - datetime.timedelta(days=7)
    weekly_expenses = Expense.objects.filter(owner=request.user, date__gte=seven_days_ago)

    weekly_data = {}
    for i in range(7):
        day = seven_days_ago + datetime.timedelta(days=i)
        total = weekly_expenses.filter(date=day).aggregate(sum=Sum('amount'))['sum'] or 0
        weekly_data[day.strftime('%Y-%m-%d')] = total

    return JsonResponse({
        'expense_category_data': finalrep,
        'weekly_data': weekly_data
    })
# -------------------------------------------------------------------------

# ✅ Properly placed and fixed stats_view()
@login_required(login_url='/authentication/login')
def stats_view(request):
    from django.db.models import Sum
    import datetime

    user = request.user
    today = datetime.date.today()

    # ✅ CATEGORY-WISE SPENDING (last 6 months)
    six_months_ago = today - datetime.timedelta(days=30 * 6)
    category_summary = (
        Expense.objects.filter(owner=user, date__gte=six_months_ago, date__lte=today)
        .values('category')
        .annotate(total=Sum('amount'))
        .order_by('category')
    )

    category_labels = [item['category'] for item in category_summary]
    category_data = [float(item['total']) for item in category_summary]

    # ✅ WEEKLY SPENDING (last 7 days)
    seven_days_ago = today - datetime.timedelta(days=6)
    daily_expenses = []
    for i in range(7):
        day = seven_days_ago + datetime.timedelta(days=i)
        total = (
            Expense.objects.filter(owner=user, date=day)
            .aggregate(sum=Sum('amount'))['sum']
            or 0
        )
        daily_expenses.append((day.strftime('%Y-%m-%d'), float(total)))

    daily_labels = [item[0] for item in daily_expenses]
    daily_data = [item[1] for item in daily_expenses]

    # ✅ Pass data to template
    context = {
        'category_labels': json.dumps(category_labels),
        'category_data': json.dumps(category_data),
        'daily_labels': json.dumps(daily_labels),
        'daily_data': json.dumps(daily_data),
    }

    return render(request, 'expenses/stats.html', context)

@login_required(login_url='/authentication/login')
def predict_category(description):
    predict_category_url = 'http://localhost:8000/api/predict-category/'
    data = {'description': description}
    response = requests.post(predict_category_url, data=data)
    if response.status_code == 200:
        predicted_category = response.json().get('predicted_category')
        return predicted_category
    else:
        return None

def set_expense_limit(request):
    if request.method == "POST":
        daily_expense_limit = request.POST.get('daily_expense_limit')
        existing_limit = ExpenseLimit.objects.filter(owner=request.user).first()
        if existing_limit:
            existing_limit.daily_expense_limit = daily_expense_limit
            existing_limit.save()
        else:
            ExpenseLimit.objects.create(owner=request.user, daily_expense_limit=daily_expense_limit)
        messages.success(request, "Daily Expense Limit Updated Successfully!")
        return HttpResponseRedirect('/preferences/')
    else:
        return HttpResponseRedirect('/preferences/')

def get_expense_of_day(user):
    current_date = date.today()
    expenses = Expense.objects.filter(owner=user, date=current_date)
    total_expenses = sum(expense.amount for expense in expenses)
    return total_expenses

@csrf_exempt
def predict_category_api(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        description = data.get('description', '')

        # Rule first
        predicted_category = rule_based_category(description)

        # ML fallback
        if not predicted_category:
            clean_desc = preprocess_text(description)
            vector = tfidf_vectorizer.transform([clean_desc])
            predicted_category = model.predict(vector)[0]

        return JsonResponse({'category': predicted_category})
