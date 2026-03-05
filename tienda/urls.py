from django.urls import path
from .views import lista_bebidas, agregar_al_carrito, ver_carrito, eliminar_del_carrito, restar_del_carrito, sumar_del_carrito

urlpatterns = [
    path('', lista_bebidas, name='lista_bebidas'),
    path('agregar/<int:bebida_id>/', agregar_al_carrito, name='agregar_al_carrito'),
    path('carrito/', ver_carrito, name='ver_carrito'),
    path('eliminar/<int:bebida_id>/', eliminar_del_carrito, name='eliminar_del_carrito'),
    path('restar/<int:bebida_id>/', restar_del_carrito, name='restar_del_carrito'),
    path('sumar/<int:bebida_id>/', sumar_del_carrito, name='sumar_del_carrito'),
]