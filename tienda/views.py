from django.shortcuts import render
from .models import Comida, Pedido, ItemPedido, Reserva
from django.shortcuts import get_object_or_404, redirect
from django.http import JsonResponse
from django.core.mail import send_mail
from django.conf import settings
import mercadopago

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

    if not carrito:
        return redirect("lista_comidas")

    total = 0

    for comida_id, cantidad in carrito.items():
        comida = get_object_or_404(Comida, id=comida_id)
        total += comida.precio * cantidad

    if request.method == "POST":

        total = 0

        nombre = request.POST.get("nombre")
        email = request.POST.get("email")
        direccion = request.POST.get("direccion")
        tipo_pedido = request.POST.get("tipo_pedido")
        forma_pago = request.POST.get("forma_pago")
        aclaraciones = request.POST.get("aclaraciones")

        pedido = Pedido.objects.create(
            nombre_cliente=nombre,
            email_cliente=email,
            direccion=direccion,
            tipo_pedido=tipo_pedido,
            forma_pago=forma_pago,
            total=0
        )

        for comida_id, cantidad in carrito.items():

            comida = get_object_or_404(Comida, id=comida_id)

            subtotal = comida.precio * cantidad
            total += subtotal

            ItemPedido.objects.create(
                pedido=pedido,
                comida=comida,
                cantidad=cantidad,
                precio=comida.precio
            )

        pedido.total = total
        pedido.save()

        request.session["carrito"] = {}

        # SI ES EFECTIVO → mandar mail directo
        if forma_pago == "efectivo":
            print("EMAIL USER:", settings.EMAIL_HOST_USER)
            print("FROM EMAIL:", settings.DEFAULT_FROM_EMAIL)

            enviar_email_pedido(pedido)

            return redirect("compra_exitosa")

        # SI ES MERCADO PAGO
        return redirect("pagar_con_mercadopago", pedido_id=pedido.id)

    return render(request, "tienda/checkout.html", {
        "total": total
    })


def enviar_email_pedido(pedido):

    items = ItemPedido.objects.filter(pedido=pedido)

    detalle_pedido = ""

    for item in items:
        subtotal = item.precio * item.cantidad
        detalle_pedido += f"{item.comida.nombre} x{item.cantidad} - ${subtotal}\n"

    mensaje = f"""
Pedido confirmado

Cliente: {pedido.nombre_cliente}

Tipo de pedido: {pedido.tipo_pedido}

Dirección:
{pedido.direccion}

Pedido:
{detalle_pedido}

Total: ${pedido.total}
"""

    send_mail(
        "Pedido confirmado - Portside",
        mensaje,
        settings.DEFAULT_FROM_EMAIL,
        [pedido.email_cliente],
    )

    send_mail(
        "Nuevo pedido recibido",
        mensaje,
        settings.DEFAULT_FROM_EMAIL,
        ["webportsidepm@gmail.com"],
    )


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

    pedido_id = request.GET.get("pedido_id")

    if pedido_id:
        pedido = Pedido.objects.get(id=pedido_id)
        pedido.pagado = True
        pedido.save()

        enviar_email_pedido(pedido)

    return render(request, "tienda/compra_exitosa.html")


def pagar_con_mercadopago(request, pedido_id):

    pedido = Pedido.objects.get(id=pedido_id)

    sdk = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)

    preference_data = {
        "items": [
            {
                "title": f"Pedido #{pedido.id}",
                "quantity": 1,
                "currency_id": "MXN",
                "unit_price": float(pedido.total)
            }
        ],
        "back_urls": {
            "success": f"http://127.0.0.1:8000/compra-exitosa/?pedido_id={pedido.id}",
            "failure": "http://127.0.0.1:8000/",
            "pending": "http://127.0.0.1:8000/"
        },
         "auto_return": "approved",
    }

    preference_response = sdk.preference().create(preference_data)
    preference = preference_response["response"]

    return redirect(preference["init_point"])