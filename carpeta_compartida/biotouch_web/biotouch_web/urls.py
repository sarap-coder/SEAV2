from django.contrib import admin
from django.urls import path
from interfaz import views

urlpatterns = [
    path('', views.home, name='home'),
    path('analisis/', views.analisis, name='analisis'),
    path('analisis/iniciar-postura/', views.iniciar_postura, name='iniciar_postura'),
    path('analisis/postura/', views.analisis_postura_live, name='analisis_postura_live'),
    path('analisis/iniciar-reflejos/', views.iniciar_evaluacion_reflejos, name='iniciar_evaluacion_reflejos'),

    path('analisis/reflejos/', views.analisis_reflejos_live, name='analisis_reflejos_live'),  # ← NUEVO

    path('video_feed/', views.video_feed, name='video_feed'),
    path('admin/', admin.site.urls),
]
