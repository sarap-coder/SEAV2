from django.contrib import admin
from django.urls import path
from interfaz import views
from django.contrib.auth.decorators import login_required

urlpatterns = [
    path('', views.home, name='home'),
    path('admin/', admin.site.urls),
    path('analisis/', login_required(views.analisis), name='analisis'),
    path('analisis/postura/', views.analisis_postura_live, name='analisis_postura_live'),
    path('analisis/reflejos/', views.analisis_reflejos_live, name='analisis_reflejos_live'),
    path('analisis/iniciar-reflejos/', views.iniciar_evaluacion_reflejos, name='iniciar_evaluacion_reflejos'),
    path('iniciar_pulso/', views.iniciar_pulso, name='iniciar_pulso'),
    path('analisis_pulso_live/', views.analisis_pulso_live, name='analisis_pulso_live'),
    path('pulse_feed/', views.pulse_feed, name='pulse_feed'),
    path('video_feed/', views.video_feed, name='video_feed'),
    path('admin/', admin.site.urls),
    path('iniciar_postura/', views.iniciar_postura, name='iniciar_postura'),
    path('analisis/otros/', views.analisis_otros, name='analisis_otros'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.salir, name='logout'),
    path('analisis/final/', views.analisis_final, name='analisis_final'),
    path('register/', views.register_view, name='register'),
    path("reflejos_feed/", views.reflejos_feed, name="reflejos_feed"),
    path('iniciar_temperatura/', views.iniciar_temperatura, name='iniciar_temperatura'),
    path('analisis_temperatura_live/', views.analisis_temperatura_live, name='analisis_temperatura_live'),
    path('temperature_feed/', views.temperature_feed, name='temperature_feed'),
    path('temperature_debug/', views.temperature_debug, name='temperature_debug'),  # Opcional para debug
    
]
