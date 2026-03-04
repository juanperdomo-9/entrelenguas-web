from django.shortcuts import render

# Create your views here.
from django.shortcuts import render
from .models import Bebida
from django.shortcuts import get_object_or_404, redirect
from django.http import JsonResponse

def lista_bebidas(request):
    bebidas = Bebida.objects.all()
    carrito = request.session.get('carrito', {})

    cantidad_carrito = sum(carrito.values())

    return render(request, 'tienda/lista.html', {
        'bebidas': bebidas,
        'carrito': carrito,
        'cantidad_carrito': cantidad_carrito
    })

from django.http import JsonResponse

def agregar_al_carrito(request, bebida_id):
    carrito = request.session.get('carrito', {})

    if str(bebida_id) in carrito:
        carrito[str(bebida_id)] += 1
    else:
        carrito[str(bebida_id)] = 1

    request.session['carrito'] = carrito

    cantidad = sum(carrito.values())

    return JsonResponse({"cantidad_carrito": cantidad})

def ver_carrito(request):
    carrito = request.session.get('carrito', {})
    bebidas = []
    total = 0

    for bebida_id, cantidad in carrito.items():
        bebida = Bebida.objects.get(id=bebida_id)
        subtotal = bebida.precio * cantidad
        total += subtotal

        bebidas.append({
            'bebida': bebida,
            'cantidad': cantidad,
            'subtotal': subtotal
        })

    return render(request, 'tienda/carrito.html', {
        'bebidas': bebidas,
        'total': total
    })

def eliminar_del_carrito(request, bebida_id):
    carrito = request.session.get('carrito', {})

    if str(bebida_id) in carrito:
        del carrito[str(bebida_id)]

    request.session['carrito'] = carrito
    return redirect('ver_carrito')

def restar_del_carrito(request, bebida_id):

    carrito = request.session.get('carrito', {})

    if str(bebida_id) in carrito:

        carrito[str(bebida_id)] -= 1

        if carrito[str(bebida_id)] <= 0:
            del carrito[str(bebida_id)]

    request.session['carrito'] = carrito

    return redirect('ver_carrito')

def sumar_del_carrito(request, bebida_id):

    carrito = request.session.get('carrito', {})

    if str(bebida_id) in carrito:
        carrito[str(bebida_id)] += 1
    else:
        carrito[str(bebida_id)] = 1

    request.session['carrito'] = carrito

    return redirect('ver_carrito')