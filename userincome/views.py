import json
import csv
import openpyxl
from io import BytesIO
from datetime import datetime, date, timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Sum, Q
from django.db.models.functions import ExtractMonth
from django.template.loader import get_template
from django.utils import timezone
from xhtml2pdf import pisa

from .models import Source, UserIncome
from expenses.models import Expense
from userpreferences.models import UserPreference


# ✅ Helper: Safe date parser (supports multiple formats)
def parse_date_safe(date_str):
    if not date_str:
        return None
    for fmt in ("%Y-%m-%d", "%B %d, %Y", "%b %d, %Y", "%b. %d, %Y"):
        try:
            return datetime.strptime(date_str.strip(), fmt).date()
        except ValueError:
            continue
    return None


@login_required(login_url='/authentication/login')
def search_income(request):
    if request.method == 'POST':
        search_str = json.loads(request.body).get('searchText')
        query = (
            Q(amount__startswith=search_str) |
            Q(date__icontains=search_str) |
            Q(description__icontains=search_str) |
            Q(source__icontains=search_str)
        )
        income = UserIncome.objects.filter(query, owner=request.user)
        data = income.values('id', 'amount', 'description', 'source', 'date')
        return JsonResponse(list(data), safe=False)


@login_required(login_url='/authentication/login')
def index(request):
    income = UserIncome.objects.filter(owner=request.user).order_by('-date')
    sort_order = request.GET.get('sort')

    if sort_order == 'amount_asc':
        income = income.order_by('amount')
    elif sort_order == 'amount_desc':
        income = income.order_by('-amount')
    elif sort_order == 'date_asc':
        income = income.order_by('date')

    paginator = Paginator(income, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    currency = UserPreference.objects.filter(user=request.user).first()
    
    context = {
        'page_obj': page_obj,
        'currency': currency.currency if currency else None,
        'sort_order': sort_order,
    }
    return render(request, 'income/index.html', context)


@login_required(login_url='/authentication/login')
def add_income(request):
    sources = Source.objects.filter(owner=request.user)
    if not sources.exists():
        messages.info(request, "You need to add income sources first in order to add income.")
        return redirect('account')

    context = {'sources': sources, 'values': request.POST}

    if request.method == 'POST':
        amount = request.POST.get('amount')
        description = request.POST.get('description')
        date_str = request.POST.get('income_date')
        source_name = request.POST.get('source')

        if not all([amount, description, date_str, source_name]):
            messages.error(request, 'All fields are required.')
            return render(request, 'income/add_income.html', context)

        try:
            date_val = datetime.strptime(date_str, '%Y-%m-%d').date()
            if date_val > timezone.now().date():
                messages.error(request, 'Date cannot be in the future.')
                return render(request, 'income/add_income.html', context)
            
            source = Source.objects.get(name=source_name, owner=request.user)

            UserIncome.objects.create(
                owner=request.user,
                amount=amount,
                date=date_val,
                source=source.name,
                description=description
            )
            messages.success(request, 'Income saved successfully.')
            return redirect('income')
            
        except Source.DoesNotExist:
            messages.error(request, 'Selected source does not exist.')
        except ValueError:
            messages.error(request, 'Invalid date format. Please use YYYY-MM-DD.')

    return render(request, 'income/add_income.html', context)


@login_required(login_url='/authentication/login')
def income_edit(request, id):
    income = get_object_or_404(UserIncome, pk=id, owner=request.user)
    sources = Source.objects.filter(owner=request.user)
    context = {'income': income, 'sources': sources}

    if request.method == 'POST':
        amount = request.POST.get('amount')
        description = request.POST.get('description')
        date_str = request.POST.get('income_date')
        source_name = request.POST.get('source')

        if not all([amount, description, date_str, source_name]):
            messages.error(request, 'All fields are required.')
            return render(request, 'income/edit_income.html', context)

        try:
            date_val = datetime.strptime(date_str, '%Y-%m-%d').date()
            if date_val > timezone.now().date():
                messages.error(request, 'Date cannot be in the future.')
                return render(request, 'income/edit_income.html', context)
            
            source = Source.objects.get(name=source_name, owner=request.user)

            income.amount = amount
            income.date = date_val
            income.source = source.name
            income.description = description
            income.save()

            messages.success(request, 'Income updated successfully.')
            return redirect('income')

        except Source.DoesNotExist:
            messages.error(request, 'Selected source does not exist.')
        except ValueError:
            messages.error(request, 'Invalid date format.')

    return render(request, 'income/edit_income.html', context)


@login_required(login_url='/authentication/login')
def delete_income(request, id):
    income = get_object_or_404(UserIncome, pk=id, owner=request.user)
    income.delete()
    messages.success(request, 'Record removed.')
    return redirect('income')


@login_required(login_url='/authentication/login')
def income_summary(request):
    user = request.user
    today = timezone.now().date()

    daily_income = UserIncome.objects.filter(owner=user, date=today).aggregate(total=Sum('amount'))['total'] or 0
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    weekly_income = UserIncome.objects.filter(owner=user, date__range=[start_of_week, end_of_week]).aggregate(total=Sum('amount'))['total'] or 0
    monthly_income = UserIncome.objects.filter(owner=user, date__year=today.year, date__month=today.month).aggregate(total=Sum('amount'))['total'] or 0
    yearly_income = UserIncome.objects.filter(owner=user, date__year=today.year).aggregate(total=Sum('amount'))['total'] or 0
    
    context = {
        'daily_income': daily_income,
        'weekly_income': weekly_income,
        'monthly_income': monthly_income,
        'yearly_income': yearly_income,
    }
    return render(request, 'income/dashboard.html', context)


@login_required(login_url='/authentication/login')
def monthly_income_data(request):
    current_year = timezone.now().year
    monthly_data = UserIncome.objects.filter(owner=request.user, date__year=current_year)\
        .annotate(month=ExtractMonth('date'))\
        .values('month')\
        .annotate(total=Sum('amount'))\
        .order_by('month')

    income_by_month = {item['month']: item['total'] for item in monthly_data}
    final_data = [income_by_month.get(i, 0) for i in range(1, 13)]

    return JsonResponse({'monthly_income_data': final_data})


def render_to_pdf(template_path, context_dict):
    template = get_template(template_path)
    html = template.render(context_dict)
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result)
    if not pdf.err:
        return result.getvalue()
    return None


@login_required(login_url='/authentication/login')
def report(request):
    return render(request, 'income/report.html')


@login_required(login_url='/authentication/login')
def generate_report(request):
    if request.method == "POST":
        start_date_str = request.POST.get('start_date')
        end_date_str = request.POST.get('end_date')

        start_date = parse_date_safe(start_date_str)
        end_date = parse_date_safe(end_date_str)

        if not start_date or not end_date:
            messages.error(request, "Invalid date format.")
            return redirect('report')
        if start_date > end_date:
            messages.error(request, "Start date cannot be after end date.")
            return redirect('report')

        incomes = UserIncome.objects.filter(owner=request.user, date__range=[start_date, end_date])
        expenses = Expense.objects.filter(owner=request.user, date__range=[start_date, end_date])

        total_income = incomes.aggregate(total=Sum('amount'))['total'] or 0
        total_expense = expenses.aggregate(total=Sum('amount'))['total'] or 0
        savings = total_income - total_expense
        
        context = {
            'incomes': incomes, 'expenses': expenses, 'total_income': total_income,
            'total_expense': total_expense, 'savings': savings, 'start_date': start_date,
            'end_date': end_date, 'report_generated': True
        }
        return render(request, 'income/report.html', context)
    return redirect('report')


@login_required(login_url='/authentication/login')
def get_report_data(request):
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')

    start_date = parse_date_safe(start_date_str)
    end_date = parse_date_safe(end_date_str)

    incomes = UserIncome.objects.filter(owner=request.user, date__range=[start_date, end_date])
    expenses = Expense.objects.filter(owner=request.user, date__range=[start_date, end_date])
    return incomes, expenses, start_date, end_date


@login_required(login_url='/authentication/login')
def export_pdf(request):
    incomes, expenses, start_date, end_date = get_report_data(request)
    total_income = incomes.aggregate(total=Sum('amount'))['total'] or 0
    total_expense = expenses.aggregate(total=Sum('amount'))['total'] or 0
    context = {
        'incomes': incomes, 'expenses': expenses, 'total_income': total_income,
        'total_expense': total_expense, 'savings': total_income - total_expense,
        'start_date': start_date, 'end_date': end_date
    }
    pdf_file = render_to_pdf('income/pdf_template.html', context)
    if pdf_file:
        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="report_{start_date}_to_{end_date}.pdf"'
        return response
    return HttpResponse("Error rendering PDF", status=500)


@login_required(login_url='/authentication/login')
def export_csv(request):
    incomes, expenses, start_date, end_date = get_report_data(request)
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="report_{start_date}_to_{end_date}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Income'])
    writer.writerow(['Date', 'Source', 'Description', 'Amount'])
    for income in incomes:
        writer.writerow([income.date, income.source, income.description, income.amount])
    writer.writerow(['Total Income', incomes.aggregate(total=Sum('amount'))['total'] or 0])
    
    writer.writerow([])
    writer.writerow(['Expenses'])
    writer.writerow(['Date', 'Category', 'Description', 'Amount'])
    for expense in expenses:
        writer.writerow([expense.date, expense.category, expense.description, expense.amount])
    writer.writerow(['Total Expenses', expenses.aggregate(total=Sum('amount'))['total'] or 0])
    
    return response


@login_required(login_url='/authentication/login')
def export_xlsx(request):
    incomes, expenses, start_date, end_date = get_report_data(request)
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="report_{start_date}_to_{end_date}.xlsx"'
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Report"
    
    ws.append(['Income'])
    ws.append(['Date', 'Source', 'Description', 'Amount'])
    for income in incomes:
        ws.append([income.date, income.source, income.description, income.amount])
    ws.append(['Total Income', incomes.aggregate(total=Sum('amount'))['total'] or 0])
    
    ws.append([])
    ws.append(['Expenses'])
    ws.append(['Date', 'Category', 'Description', 'Amount'])
    for expense in expenses:
        ws.append([expense.date, expense.category, expense.description, expense.amount])
    ws.append(['Total Expenses', expenses.aggregate(total=Sum('amount'))['total'] or 0])
    
    wb.save(response)
    return response
