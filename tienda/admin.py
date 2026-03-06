from django.contrib import admin
from .models import Comida, Pedido, ItemPedido, Reserva


admin.site.register(Comida)


class ItemPedidoInline(admin.TabularInline):
    model = ItemPedido
    extra = 0


class PedidoAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "nombre_cliente",
        "email_cliente",
        "total",
        "pagado",
        "enviado",
        "fecha"
    )

    list_filter = ("pagado", "enviado")

    inlines = [ItemPedidoInline]


admin.site.register(Pedido, PedidoAdmin)
admin.site.register(Reserva)