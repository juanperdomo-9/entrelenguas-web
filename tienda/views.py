from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.conf import settings
from .models import Comida, Pedido, ItemPedido, Reserva
import mercadopago
import resend
import os

# CONFIGURAR RESEND
resend.api_key = os.environ.get("RESEND_API_KEY")


def enviar_correo(destino, asunto, mensaje):

    resend.Emails.send({
        "from": "Portside <reservas@portsidepm.com>",
        "to": [destino],
        "subject": asunto,
        "html": f"<pre>{mensaje}</pre>"
    })


def lista_comidas(request):
    comidas = Comida.objects.all()
    carrito = request.session.get('carrito', {})

    cantidad_carrito = sum(carrito.values())

    return render(request, 'tienda/lista.html', {
        'comidas': comidas,
        'carrito': carrito,
        'cantidad_carrito': cantidad_carrito
    })

def home_en(request):

    carrito = request.session.get('carrito', {})
    cantidad_carrito = sum(carrito.values())

    return render(request, "tienda/home_en.html", {
        "cantidad_carrito": cantidad_carrito
    })

def pickup_comida(request):

    comidas = Comida.objects.filter(tipo="comida")

    carrito = request.session.get('carrito', {})
    cantidad_carrito = sum(carrito.values())

    return render(request, "tienda/pickup_comida.html", {
        "comidas": comidas,
        "cantidad_carrito": cantidad_carrito
    })


def pickup_vinos(request):

    comidas = Comida.objects.filter(tipo="vino")

    carrito = request.session.get('carrito', {})
    cantidad_carrito = sum(carrito.values())

    return render(request, "tienda/pickup_vinos.html", {
        "comidas": comidas,
        "cantidad_carrito": cantidad_carrito
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

        # SI ES EFECTIVO
        if forma_pago == "efectivo":

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

    enviar_correo(
        pedido.email_cliente,
        "Pedido confirmado - Portside",
        mensaje
    )

    enviar_correo(
        "webportsidepm@gmail.com",
        "Nuevo pedido recibido",
        mensaje
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
            hora=hora,
            email=email_cliente
        )

        mensaje = f"""
Nueva reserva

Nombre: {nombre}
Telefono: {telefono}
Personas: {personas}
Fecha: {fecha}
Hora: {hora}
"""

        enviar_correo(
            "webportsidepm@gmail.com",
            "Nueva reserva en el restaurante",
            mensaje
        )

        enviar_correo(
            email_cliente,
            "Reserva confirmada",
            f"Hola {nombre}, tu reserva fue confirmada para {fecha} a las {hora}."
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
    "success": f"https://portsidepm.com/compra-exitosa/?pedido_id={pedido.id}",
    "failure": "https://portsidepm.com/",
    "pending": "https://portsidepm.com/"
    },
    "auto_return": "approved",
    }

    preference_response = sdk.preference().create(preference_data)
    preference = preference_response["response"]

    return redirect(preference["init_point"])


def test_email(request):

    try:

        enviar_correo(
            "clientesportsidepm@gmail.com",
            "Test Email",
            "Correo de prueba desde Portside"
        )

        return HttpResponse("Email enviado")

    except Exception as e:

        return HttpResponse(f"Error: {str(e)}")
    
def pickup_food_en(request):

    comidas = Comida.objects.filter(tipo="comida")

    carrito = request.session.get('carrito', {})
    cantidad_carrito = sum(carrito.values())

    return render(request,"tienda/pickup_food_en.html",{
        "comidas": comidas,
        "cantidad_carrito": cantidad_carrito
    })


def pickup_wine_en(request):

    comidas = Comida.objects.filter(tipo="vino")

    carrito = request.session.get('carrito', {})
    cantidad_carrito = sum(carrito.values())

    return render(request,"tienda/pickup_wine_en.html",{
        "comidas": comidas,
        "cantidad_carrito": cantidad_carrito
    })