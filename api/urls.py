from django.urls import path
from . import views

urlpatterns = [
    path('expenses/', views.ExpenseListAPIView.as_view(), name='expenses-api'),
    path('expenses/create/', views.ExpenseCreateAPIView.as_view(), name='create-expense-api'),
    path('expenses/<int:pk>/', views.ExpenseDetailAPIView.as_view(), name='expense-detail-api'),
    
    # --- YEH NAYI URL ADD KAREIN ---
    path('dashboard-stats/', views.DashboardStatsAPIView.as_view(), name='dashboard-stats-api'),
    
    path('predict-category/', views.PredictCategory.as_view(), name='predict-category'),
    path('update-dataset/', views.UpdateDataset.as_view(), name='update-dataset'),
]