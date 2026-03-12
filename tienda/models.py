from django.db import models


class Comida(models.Model):

    TIPO_CHOICES = [
        ("comida", "Comida"),
        ("vino", "Vino"),
    ]

    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default="comida")

    nombre = models.CharField(max_length=100)
    descripcion = models.TextField()
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    imagen = models.ImageField(upload_to='comidas/')
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

    enviado = models.BooleanField(default=False)

    tipo_pedido = models.CharField(
        max_length=20,
        choices=[
            ("delivery", "Delivery"),
            ("retiro", "Retiro en el local")
        ]
    )

    forma_pago = models.CharField(
        max_length=20,
        choices=[
            ("efectivo", "Efectivo"),
            ("mp", "Mercado Pago")
        ],
        default="efectivo"
    )

    def __str__(self):
        return f"Pedido {self.id} - {self.nombre_cliente}"


class ItemPedido(models.Model):

    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE)
    comida = models.ForeignKey(Comida, on_delete=models.CASCADE)

    cantidad = models.IntegerField()
    precio = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.comida.nombre} x{self.cantidad}"


class Reserva(models.Model):

    nombre = models.CharField(max_length=200)
    telefono = models.CharField(max_length=50)
    personas = models.IntegerField()
    email = models.EmailField()

    fecha = models.DateField()
    hora = models.TimeField()

    creado = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nombre} - {self.fecha} {self.hora}"