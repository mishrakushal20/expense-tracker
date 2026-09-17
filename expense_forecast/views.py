# from django.shortcuts import render
# import numpy as np
# import pandas as pd
# from statsmodels.tsa.arima.model import ARIMA
# import matplotlib.pyplot as plt
# from django.utils.timezone import now
# from expenses.models import Expense
# from django.http import HttpResponse
# from django.contrib import messages

# # Fetch the data from the Expense model and create the forecast
# def forecast(request):
#     # Fetch the latest 30 expenses for the current user
#     expenses = Expense.objects.filter(owner=request.user).order_by('-date')[:30]

#     # Check if there are enough expenses for forecasting
#     if len(expenses) < 10:
#         messages.error(request, "Not enough expenses to make a forecast. Please add more expenses.")
#         return render(request, 'expense_forecast/index.html')

#     # Create a DataFrame from the expenses
#     data = pd.DataFrame({'Date': [expense.date for expense in expenses], 'Expenses': [expense.amount for expense in expenses]})
#     data.set_index('Date', inplace=True)

#     # Fit ARIMA model
#     model = ARIMA(data['Expenses'], order=(5, 1, 0))
#     model_fit = model.fit()

#     # Forecast next 30 days of expenses starting from the next day
#     forecast_steps = 30
#     current_date = now().date()
#     next_day = current_date + pd.DateOffset(days=1)
#     forecast_index = pd.date_range(start=next_day, periods=forecast_steps, freq='D')

#     # Predict the future expenses
#     forecast = model_fit.forecast(steps=forecast_steps)

#     # Create a DataFrame for the forecasted expenses
#     forecast_data = pd.DataFrame({'Date': forecast_index, 'Forecasted_Expenses': forecast})
    
#     # Convert the forecast data to a list of dictionaries
#     forecast_data_list = forecast_data.reset_index().to_dict(orient='records')

#     # Create a plot but save it without displaying it
#     plt.figure(figsize=(10, 6))
#     plt.plot(data, label='Previous Expenses')
#     plt.plot(forecast_index, forecast, label='Forecasted Expenses', color='red')
#     plt.xlabel('Date')
#     plt.ylabel('Expenses')
#     plt.title('Expense Forecast for Next 30 Days')
#     plt.legend()

#     # Save the plot to a file without displaying it
#     plot_file = 'static/img/forecast_plot.png'
#     plt.savefig(plot_file)
#     plt.close()

#     # Pass the data to the template
#     context = {
#         'forecast_data': forecast_data_list,
#         'plot_file': plot_file,
#         'total_forecasted_expenses': np.sum(forecast),
#     }

#     return render(request, 'expense_forecast/index.html', context)

from django.shortcuts import render
import numpy as np
import pandas as pd
from statsmodels.tsa.arima.model import ARIMA
from django.utils.timezone import now
from expenses.models import Expense
from django.http import HttpResponse
from django.contrib import messages
import matplotlib.pyplot as plt
from django.contrib.auth.decorators import login_required


@login_required(login_url='/authentication/login')
def forecast(request):
    expenses = Expense.objects.filter(owner=request.user)

    if expenses.count() < 10:
        messages.error(request, "Not enough expenses to make a forecast.")
        return render(request, 'expense_forecast/index.html')

    # ✅ Convert to DataFrame
    data = pd.DataFrame({
        'date': [e.date for e in expenses],
        'amount': [e.amount for e in expenses],
        'category': [e.category for e in expenses]
    })

    # ✅ FIX 1: sort properly
    data['date'] = pd.to_datetime(data['date'])
    data = data.sort_values('date')

    # ✅ FIX 2: merge same dates
    data = data.groupby('date').sum().reset_index()

    # ✅ FIX 3: set index
    data.set_index('date', inplace=True)

    # ✅ FIX 4: fill missing dates
    data = data.asfreq('D')

    # ✅ FIX 5: fill missing values
    data['amount'] = data['amount'].fillna(method='ffill')
    data['amount'] = data['amount'].fillna(0)

    # ✅ SAFETY CHECK
    if data['amount'].nunique() < 2:
        messages.error(request, "Not enough variation in data for forecasting.")
        return render(request, 'expense_forecast/index.html')

    try:
        # ✅ FIXED MODEL (simpler = stable)
        model = ARIMA(data['amount'], order=(1, 1, 1))
        model_fit = model.fit()
    except:
        messages.error(request, "Forecast failed. Try adding more consistent data.")
        return render(request, 'expense_forecast/index.html')

    # ✅ Forecast next 30 days
    forecast_steps = 30
    forecast = model_fit.forecast(steps=forecast_steps)
    forecast = forecast.round().astype(int)

    forecast_index = pd.date_range(
        start=data.index[-1] + pd.Timedelta(days=1),
        periods=forecast_steps,
        freq='D'
    )

    forecast_data = pd.DataFrame({
        'Date': forecast_index,
        'Forecasted_Expenses': forecast
    })

    forecast_data_list = forecast_data.reset_index().to_dict(orient='records')

    total_forecasted_expenses = int(np.sum(forecast))

    category_forecasts = (
        pd.DataFrame({
            'category': [e.category for e in expenses],
            'amount': [e.amount for e in expenses]
        })
        .groupby('category')['amount']
        .sum()
        .to_dict()
    )

    # ✅ Plot
    plt.figure(figsize=(10, 6))
    plt.plot(data.index, data['amount'], label='Past Expenses')
    plt.plot(forecast_index, forecast, label='Forecast', color='red')
    plt.legend()

    plot_file = 'static/img/forecast_plot.png'
    plt.savefig(plot_file)
    plt.close()

    context = {
        'forecast_data': forecast_data_list,
        'total_forecasted_expenses': total_forecasted_expenses,
        'category_forecasts': category_forecasts,
    }

    return render(request, 'expense_forecast/index.html', context)