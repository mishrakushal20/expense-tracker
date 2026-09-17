from django.urls import path
from . import views
urlpatterns = [
    path('', views.userprofile, name="profile"),
    path('addSource/',views.addSource,name="addSource"),
    path('deleteSource/<int:id>',views.deleteSource,name="deleteSource")
]
