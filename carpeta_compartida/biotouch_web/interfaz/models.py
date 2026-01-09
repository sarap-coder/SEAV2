from django.db import models
from django.contrib.auth.models import User

class AnalisisMedico(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    completado_postura = models.BooleanField(default=False)
    completado_reflejos = models.BooleanField(default=False)
    completado_pulso = models.BooleanField(default=False)
    completado_temperatura = models.BooleanField(default=False)
    fecha = models.DateTimeField(auto_now_add=True)

    def completado_todo(self):
        return (
            self.completado_postura and
            self.completado_reflejos and
            self.completado_pulso and
            self.completado_temperatura
        )


class ResultadoSesion(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    fecha = models.DateTimeField(auto_now_add=True)

    # 🔹 Postura desglosada
    postura_hombros = models.CharField(max_length=50)
    postura_cadera = models.CharField(max_length=50)
    postura_torso = models.CharField(max_length=50)

    # 🔹 Resto de datos
    temperatura = models.FloatField()
    pulso = models.CharField(max_length=64)
    reflejos = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.user.username} | {self.fecha}"
