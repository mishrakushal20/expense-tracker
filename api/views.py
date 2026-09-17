# api/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics.pairwise import cosine_similarity
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
import nltk
import json
from rest_framework.permissions import IsAuthenticated
# Serializer ka naam theek kiya gaya hai
from .serializers import ExpenseSerializer
# Expense model ko import kiya gaya hai
from expenses.models import Expense
# Naye view ke liye generics ko import kiya gaya hai
from rest_framework import generics
# --- Naye Dashboard ke liye Imports ---
from datetime import timedelta
from django.db.models import Sum
import datetime


nltk.download('punkt')
nltk.download('stopwords')


# --- EXPENSE LIST DIKHANE KE LIYE VIEW ---
class ExpenseListAPIView(generics.ListAPIView):
    serializer_class = ExpenseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Expense.objects.filter(owner=self.request.user)

# --- NAYA EXPENSE ADD KARNE KE LIYE VIEW ---
class ExpenseCreateAPIView(generics.CreateAPIView):
    serializer_class = ExpenseSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

# --- EK SPECIFIC EXPENSE KO DELETE/EDIT KARNE KE LIYE VIEW ---
class ExpenseDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ExpenseSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'pk'

    def get_queryset(self):
        return Expense.objects.filter(owner=self.request.user)

# --- NAYE DASHBOARD KE LIYE API VIEW ---
class DashboardStatsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Category summary data (Pie Chart ke liye)
        category_summary = Expense.objects.filter(owner=request.user) \
            .values('category').annotate(total=Sum('amount'))
        
        category_labels = [item['category'] for item in category_summary]
        category_data = [float(item['total']) for item in category_summary]

        # Weekly summary data (Line Chart ke liye)
        today = datetime.date.today()
        seven_days_ago = today - timedelta(days=6)
        daily_summary = Expense.objects.filter(owner=request.user, date__gte=seven_days_ago) \
            .values('date').annotate(total=Sum('amount')).order_by('date')

        daily_spending = { (today - timedelta(days=i)).strftime('%Y-%m-%d'): 0 for i in range(7) }
        for entry in daily_summary:
            daily_spending[entry['date'].strftime('%Y-%m-%d')] = float(entry['total'])
        
        daily_labels = list(daily_spending.keys())
        daily_data = list(daily_spending.values())

        # Poora data ek saath bhejna
        data = {
            'category_summary': {
                'labels': category_labels,
                'data': category_data
            },
            'weekly_summary': {
                'labels': daily_labels,
                'data': daily_data
            }
        }
        return Response(data, status=status.HTTP_200_OK)


# --- AAPKA PURANA ML CODE (UNCHANGED) ---
class PredictCategory(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        user_input = request.data.get('description')
        data = pd.read_csv('dataset.csv')
        tfidf_vectorizer = TfidfVectorizer()
        data['clean_description'] = data['description'].apply(preprocess_text)
        X = tfidf_vectorizer.fit_transform(data['clean_description'])
        model = RandomForestClassifier()
        model.fit(X, data['category'])
        
        user_input_processed = preprocess_text(user_input)
        user_input_vector = tfidf_vectorizer.transform([user_input_processed])
        
        predicted_category = model.predict(user_input_vector)

        return Response({'predicted_category': predicted_category[0]}, status=status.HTTP_200_OK)


class UpdateDataset(APIView):
    def post(self, request):
       new_data = request.data.get('new_data')
       if 'description' in new_data and 'category' in new_data:
            data = pd.read_csv('dataset.csv')
            new_row = pd.DataFrame([new_data])
            data = pd.concat([data, new_row], ignore_index=True)
            data.to_csv('dataset.csv', index=False)
            return Response({'message': 'Dataset updated successfully.'}, status=status.HTTP_200_OK)
       return Response({'error': 'Invalid data provided.'}, status=status.HTTP_400_BAD_REQUEST)


def preprocess_text(text):
    stop_words = set(stopwords.words('english'))
    tokens = word_tokenize(text.lower())
    tokens = [t for t in tokens if t.isalnum() and t not in stop_words]
    return ' '.join(tokens)