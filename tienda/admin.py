from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Bebida, Pedido

admin.site.register(Bebida)
admin.site.register(Pedido)
