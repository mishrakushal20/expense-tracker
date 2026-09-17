"""
URL configuration for expensetracker project.
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('expenses.urls')),
    path('authentication/', include('authentication.urls')),
    path('preferences/', include('userpreferences.urls')),
    path('income/', include('userincome.urls')),
    path('forecast/', include('expense_forecast.urls')),
    path('api/', include('api.urls')),
    path('goals/', include('goals.urls')),
    path('profile/', include('userprofile.urls')),
    path('report/', include('report_generation.urls')),
]