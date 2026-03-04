from django.db import models

# Create your models here.


class Bebida(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField()
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    imagen = models.ImageField(upload_to='bebidas/')
    stock = models.IntegerField(default=0)

    def __str__(self):
        return self.nombre
