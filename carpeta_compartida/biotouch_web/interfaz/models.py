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
