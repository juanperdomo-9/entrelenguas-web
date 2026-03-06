from django.urls import path
from .views import lista_comidas, agregar_al_carrito, ver_carrito, eliminar_del_carrito, restar_del_carrito, sumar_del_carrito, checkout, crear_reserva, reserva_confirmada, compra_exitosa

urlpatterns = [
    path('', lista_comidas, name='lista_comidas'),
    path('agregar/<int:comida_id>/', agregar_al_carrito, name='agregar_al_carrito'),
    path('carrito/', ver_carrito, name='ver_carrito'),
    path('eliminar/<int:comida_id>/', eliminar_del_carrito, name='eliminar_del_carrito'),
    path('restar/<int:comida_id>/', restar_del_carrito, name='restar_del_carrito'),
    path('sumar/<int:comida_id>/', sumar_del_carrito, name='sumar_del_carrito'),
    path('checkout/', checkout, name='checkout'),
    path('reservar/', crear_reserva, name='crear_reserva'),
    path('reserva-confirmada/', reserva_confirmada, name='reserva_confirmada'),
    path('compra-exitosa/', compra_exitosa, name='compra_exitosa'),
]