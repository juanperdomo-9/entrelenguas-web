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

class Pedido(models.Model):

    nombre_cliente = models.CharField(max_length=200)
    email_cliente = models.EmailField()
    direccion = models.CharField(max_length=300)

    total = models.DecimalField(max_digits=10, decimal_places=2)

    fecha = models.DateTimeField(auto_now_add=True)

    pagado = models.BooleanField(default=False)

    def __str__(self):
        return f"Pedido {self.id} - {self.nombre_cliente}"