from django.contrib import admin
from django.urls import path
from interfaz import views

urlpatterns = [
    path('', views.home, name='home'),
    path('analisis/', views.analisis, name='analisis'),
    path('analisis/postura/', views.analisis_postura_live, name='analisis_postura_live'),
    path('analisis/reflejos/', views.analisis_reflejos_live, name='analisis_reflejos_live'),
    path('analisis/iniciar-reflejos/', views.iniciar_evaluacion_reflejos, name='iniciar_evaluacion_reflejos'),
    path('analisis/pulso/', views.analisis_pulso_live, name='analisis_pulso_live'),  # NEW
    path('analisis/iniciar-pulso/', views.iniciar_pulso, name='iniciar_pulso'),  # NEW
    path('video_feed/', views.video_feed, name='video_feed'),
    path('admin/', admin.site.urls),
    path('pulse_feed/', views.pulse_feed, name='pulse_feed'),
    path('iniciar_postura/', views.iniciar_postura, name='iniciar_postura')

]
