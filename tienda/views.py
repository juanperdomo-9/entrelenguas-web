from django.shortcuts import render
from .models import Comida, Pedido, ItemPedido, Reserva
from django.shortcuts import get_object_or_404, redirect
from django.http import JsonResponse
from django.core.mail import send_mail
from django.conf import settings


def lista_comidas(request):
    comidas = Comida.objects.all()
    carrito = request.session.get('carrito', {})

    cantidad_carrito = sum(carrito.values())

    return render(request, 'tienda/lista.html', {
        'comidas': comidas,
        'carrito': carrito,
        'cantidad_carrito': cantidad_carrito
    })


def agregar_al_carrito(request, comida_id):
    carrito = request.session.get('carrito', {})

    if str(comida_id) in carrito:
        carrito[str(comida_id)] += 1
    else:
        carrito[str(comida_id)] = 1

    request.session['carrito'] = carrito

    cantidad = sum(carrito.values())

    return JsonResponse({"cantidad_carrito": cantidad})


def ver_carrito(request):
    carrito = request.session.get('carrito', {})
    comidas = []
    total = 0

    for comida_id, cantidad in carrito.items():
        comida = Comida.objects.get(id=comida_id)
        subtotal = comida.precio * cantidad
        total += subtotal

        comidas.append({
            'comida': comida,
            'cantidad': cantidad,
            'subtotal': subtotal
        })

    return render(request, 'tienda/carrito.html', {
        'comidas': comidas,
        'total': total
    })


def eliminar_del_carrito(request, comida_id):
    carrito = request.session.get('carrito', {})

    if str(comida_id) in carrito:
        del carrito[str(comida_id)]

    request.session['carrito'] = carrito
    return redirect('ver_carrito')


def restar_del_carrito(request, comida_id):

    carrito = request.session.get('carrito', {})

    if str(comida_id) in carrito:

        carrito[str(comida_id)] -= 1

        if carrito[str(comida_id)] <= 0:
            del carrito[str(comida_id)]

    request.session['carrito'] = carrito

    return redirect('ver_carrito')


def sumar_del_carrito(request, comida_id):

    carrito = request.session.get('carrito', {})

    if str(comida_id) in carrito:
        carrito[str(comida_id)] += 1
    else:
        carrito[str(comida_id)] = 1

    request.session['carrito'] = carrito

    return redirect('ver_carrito')


def checkout(request):

    carrito = request.session.get("carrito", {})
    total = 0

    for comida_id, cantidad in carrito.items():

        comida = Comida.objects.get(id=comida_id)

        total += comida.precio * cantidad


    if request.method == "POST":

        total = 0

        nombre = request.POST.get("nombre")
        email = request.POST.get("email")
        direccion = request.POST.get("direccion")
        tipo_pedido = request.POST.get("tipo_pedido")
        aclaraciones = request.POST.get("aclaraciones")

        pedido = Pedido.objects.create(

            nombre_cliente=nombre,
            email_cliente=email,
            direccion=direccion,
            tipo_pedido=tipo_pedido,
            total=0

        )

        detalle_pedido = ""

        for comida_id, cantidad in carrito.items():

            comida = Comida.objects.get(id=comida_id)

            subtotal = comida.precio * cantidad
            total += subtotal

            ItemPedido.objects.create(

                pedido=pedido,
                comida=comida,
                cantidad=cantidad,
                precio=comida.precio

            )

            detalle_pedido += f"{comida.nombre} x{cantidad} - ${subtotal}\n"


        pedido.total = total
        pedido.save()

        request.session["carrito"] = {}


        # EMAIL AL CLIENTE

        mensaje_cliente = f"""
Hola {nombre},

Tu pedido fue recibido correctamente.

Tipo de pedido: {tipo_pedido}

Dirección:
{direccion}

Aclaraciones:
{aclaraciones}

Pedido:
{detalle_pedido}

Total: ${total}

Gracias por elegir Entre Lenguas.
"""

        send_mail(

            "Pedido confirmado - Entre Lenguas",
            mensaje_cliente,
            settings.DEFAULT_FROM_EMAIL,
            [email],

        )


        # EMAIL AL RESTAURANTE

        mensaje_restaurante = f"""
Nuevo pedido recibido

Cliente: {nombre}
Email: {email}

Tipo de pedido: {tipo_pedido}

Dirección:
{direccion}

Aclaraciones:
{aclaraciones}

Pedido:
{detalle_pedido}

Total: ${total}
"""

        send_mail(

            "Nuevo pedido recibido",
            mensaje_restaurante,
            settings.DEFAULT_FROM_EMAIL,
            ["webportsidepm@gmail.com"],

        )

        return redirect("compra_exitosa")


    return render(request, "tienda/checkout.html", {

        "total": total

    })


def crear_reserva(request):

    if request.method == "POST":

        nombre = request.POST.get("nombre")
        telefono = request.POST.get("telefono")
        personas = request.POST.get("personas")
        fecha = request.POST.get("fecha")
        hora = request.POST.get("hora")
        email_cliente = request.POST.get("email")

        Reserva.objects.create(
            nombre=nombre,
            telefono=telefono,
            personas=personas,
            fecha=fecha,
            hora=hora
        )

        mensaje = f"""
Nueva reserva

Nombre: {nombre}
Telefono: {telefono}
Personas: {personas}
Fecha: {fecha}
Hora: {hora}
"""

        send_mail(
            "Nueva reserva en el restaurante",
            mensaje,
            settings.DEFAULT_FROM_EMAIL,
            ["webportsidepm@gmail.com"],
            fail_silently=False,
        )

        send_mail(
            "Reserva confirmada",
            f"Hola {nombre}, tu reserva fue confirmada para {fecha} a las {hora}.",
            settings.DEFAULT_FROM_EMAIL,
            [email_cliente],
        )

        return redirect("reserva_confirmada")


def reserva_confirmada(request):
    return render(request, 'tienda/reserva_confirmada.html')


def compra_exitosa(request):
    return render(request, "tienda/compra_exitosa.html")