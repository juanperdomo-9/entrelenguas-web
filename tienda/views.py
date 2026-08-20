from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.conf import settings
from .models import Comida, Pedido, ItemPedido, Reserva
import mercadopago
import resend
import requests
import anthropic
import json
import os

# CONFIGURAR RESEND
resend.api_key = os.environ.get("RESEND_API_KEY")

# ⚠️ EDITAR ACÁ las ofertas / happy hour del local.
# Este texto es lo único que el bot conoce sobre promociones: si cambia el
# happy hour o hay una promo nueva, se actualiza acá.
INFO_OFERTAS = """
- Happy Hour: todos los días de 17:00 a 19:00 hs. 2x1 en cócteles de la casa
  y mezcales seleccionados.
- Cerrado los miércoles (todo el día).
- Pickup / retiro en el local disponible para comida y vinos (ver botón
  "Order Online" en el menú del sitio).
- Delivery disponible según zona (Puerto Morelos y alrededores).
""".strip()

# El idioma de respuesta lo define la página donde está el widget (ES u EN),
# NO el idioma en el que escribe la persona — así el bot de la página en
# inglés siempre contesta en inglés aunque le escriban en español, y viceversa.
CHAT_SYSTEM_PROMPT = """You are the virtual assistant for Portside, an \
international-cuisine restaurant in Puerto Morelos, Quintana Roo, Mexico. \
Answer ONLY questions about the menu, prices, hours, promotions/happy hour, \
reservations, pickup and delivery, using exclusively the information provided \
below. If asked something not covered there (e.g. a specific dish), say you \
don't have that info and suggest WhatsApp or the site's menu. Never invent \
prices, hours or promotions. Regardless of the language the visitor writes \
in, ALWAYS answer in {idioma_nombre} — this is a hard requirement, not a \
preference. Keep answers to 2-3 sentences max, warm and friendly tone.

Restaurant info:
{ofertas}
"""

IDIOMAS = {
    "es": "Spanish",
    "en": "English",
}


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

# Textos fijos por idioma de página (ES = home '/', EN = home '/en').
TEXTOS_CHAT = {
    "es": {
        "solicitud_invalida": "Solicitud inválida.",
        "sin_mensaje": "Escribí una pregunta.",
        "muy_largo": "Mensaje demasiado largo.",
        "limite": "Por hoy llegamos al límite de preguntas por acá 🙏 "
                  "Escribinos por WhatsApp y te ayudamos.",
        "no_activado": "El asistente todavía no está activado. "
                       "Escribinos por WhatsApp mientras tanto 💬",
        "sin_dato": "No tengo esa información. Escribinos por WhatsApp.",
        "rate_limit": "Estamos con mucha demanda ahora mismo, probá de nuevo en un rato.",
        "error_api": "Tuvimos un problema para responder. Escribinos por WhatsApp.",
        "error_conexion": "No pudimos conectar con el asistente. Escribinos por WhatsApp.",
    },
    "en": {
        "solicitud_invalida": "Invalid request.",
        "sin_mensaje": "Type a question.",
        "muy_largo": "Message is too long.",
        "limite": "We hit today's question limit here 🙏 "
                  "Message us on WhatsApp and we'll help you out.",
        "no_activado": "The assistant isn't active yet. "
                       "Message us on WhatsApp in the meantime 💬",
        "sin_dato": "I don't have that info. Message us on WhatsApp.",
        "rate_limit": "We're getting a lot of questions right now, try again shortly.",
        "error_api": "We had trouble answering. Message us on WhatsApp.",
        "error_conexion": "Couldn't reach the assistant. Message us on WhatsApp.",
    },
}


@require_POST
def chat_bot(request):
    """Responde preguntas de clientes sobre ofertas/happy hour/horarios.

    El idioma de respuesta lo decide la página que llama (parámetro
    "idioma": "es" | "en" en el body), no el idioma del mensaje.
    """

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, TypeError):
        return JsonResponse({"error": "Solicitud inválida."}, status=400)

    idioma = data.get("idioma") if data.get("idioma") in IDIOMAS else "es"
    textos = TEXTOS_CHAT[idioma]

    mensaje = (data.get("mensaje") or "").strip()

    if not mensaje:
        return JsonResponse({"error": textos["sin_mensaje"]}, status=400)

    if len(mensaje) > 500:
        return JsonResponse({"error": textos["muy_largo"]}, status=400)

    # Límite simple por sesión para evitar abuso del costo de la API.
    usados = request.session.get("chat_bot_usos", 0)

    if usados >= 30:
        return JsonResponse({"respuesta": textos["limite"]})

    if not os.environ.get("ANTHROPIC_API_KEY"):
        return JsonResponse({"respuesta": textos["no_activado"]})

    try:
        respuesta = anthropic.Anthropic().messages.create(
            model="claude-opus-5",
            max_tokens=300,
            output_config={"effort": "low"},
            system=CHAT_SYSTEM_PROMPT.format(
                idioma_nombre=IDIOMAS[idioma],
                ofertas=INFO_OFERTAS,
            ),
            messages=[{"role": "user", "content": mensaje}],
        )
        texto = next(
            (b.text for b in respuesta.content if b.type == "text"),
            textos["sin_dato"]
        )

    except anthropic.RateLimitError:
        texto = textos["rate_limit"]
    except anthropic.APIStatusError:
        texto = textos["error_api"]
    except anthropic.APIConnectionError:
        texto = textos["error_conexion"]

    request.session["chat_bot_usos"] = usados + 1

    return JsonResponse({"respuesta": texto})


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

    ZONAS = {
        "zona1": 0,
        "zona2": 70,
        "zona3": 100,
        "zona4": 130
    }

    carrito = request.session.get("carrito", {})

    if not carrito:
        return redirect("lista_comidas")

    total = 0

    for comida_id, cantidad in carrito.items():
        comida = get_object_or_404(Comida, id=comida_id)
        total += comida.precio * cantidad

    if request.method == 'POST':

        # 🔴 1. Obtener token del captcha
        token = request.POST.get('g-recaptcha-response')

        # 🔴 2. Validar captcha
        if not verificar_recaptcha(token):
            return HttpResponse("Captcha inválido, intentá nuevamente.")

        total = 0

        nombre = request.POST.get("nombre")
        email = request.POST.get("email")
        direccion = request.POST.get("direccion")
        tipo_pedido = request.POST.get("tipo_pedido")
        zona = request.POST.get("zona")
        forma_pago = request.POST.get("forma_pago")
        aclaraciones = request.POST.get("aclaraciones")

        pedido = Pedido.objects.create(
            nombre_cliente=nombre,
            email_cliente=email,
            direccion=direccion,
            tipo_pedido=tipo_pedido,
            forma_pago=forma_pago,
            total=0,
            zona=zona
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

        # 🚚 SUMAR ENVÍO SOLO SI ES DELIVERY
        if tipo_pedido == "delivery":
            if not zona:
                return HttpResponse("Seleccioná tu zona de entrega")

            if zona in ZONAS:
                total += ZONAS[zona]

        pedido.total = total
        pedido.save()

        request.session["carrito"] = {}

        # 💵 EFECTIVO
        if forma_pago == "efectivo":
            enviar_email_pedido(pedido)
            return redirect("compra_exitosa")

        # 💳 MERCADO PAGO
        return redirect("pagar_con_mercadopago", pedido_id=pedido.id)

    return render(request, "tienda/checkout.html", {
        "total": total,
    })


def enviar_email_pedido(pedido):

    ZONAS = {
        "zona1": 0,
        "zona2": 70,
        "zona3": 100,
        "zona4": 130
    }

    items = ItemPedido.objects.filter(pedido=pedido)

    detalle_pedido = ""
    subtotal_total = 0

    for item in items:
        subtotal = item.precio * item.cantidad
        subtotal_total += subtotal
        detalle_pedido += f"{item.comida.nombre} x{item.cantidad} - ${subtotal}\n"

    envio = 0
    zona = getattr(pedido, "zona", None)

    if pedido.tipo_pedido == "delivery" and zona in ZONAS:
        envio = ZONAS[zona]

    # 📧 CLIENTE
    mensaje_cliente = f"""
Hola {pedido.nombre_cliente},

Tu pedido fue confirmado 🎉

Tipo: {pedido.tipo_pedido}
Dirección: {pedido.direccion}

Detalle:
{detalle_pedido}

Subtotal: ${subtotal_total}
Envío: ${envio}
Total: ${pedido.total}

Gracias por elegir Portside 🙌
"""

    # 📧 NEGOCIO
    mensaje_admin = f"""
Nuevo pedido 🚨

Cliente: {pedido.nombre_cliente}
Email: {pedido.email_cliente}

Tipo: {pedido.tipo_pedido}
Zona: {zona}
Dirección: {pedido.direccion}

Detalle:
{detalle_pedido}

Subtotal: ${subtotal_total}
Envío: ${envio}
Total: ${pedido.total}
"""

    enviar_correo(
        pedido.email_cliente,
        "Confirmación de pedido - Portside",
        mensaje_cliente
    )

    enviar_correo(
        "webportsidepm@gmail.com",
        "Nuevo pedido recibido",
        mensaje_admin
    )


def crear_reserva(request):

    if request.method == 'POST':
        token = request.POST.get('g-recaptcha-response')

        if not verificar_recaptcha(token):
            return HttpResponse("Captcha inválido")

        nombre = request.POST.get("nombre")
        telefono = request.POST.get("telefono")
        personas = request.POST.get("personas")
        fecha = request.POST.get("fecha")
        from datetime import datetime

        fecha_obj = datetime.strptime(fecha, "%Y-%m-%d")
        if fecha_obj.weekday() == 2:
            return HttpResponse(
                "Lo sentimos, el restaurante permanece cerrado los miércoles."
            )
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

    return render(request,"tienda/pickup_wines_en.html",{
        "comidas": comidas,
        "cantidad_carrito": cantidad_carrito
    })

def cart_en(request):

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

    return render(request,"tienda/cart_en.html",{
        "comidas": comidas,
        "total": total
    })


def checkout_en(request):

    ZONAS = {
        "zona1": 0,
        "zona2": 70,
        "zona3": 100,
        "zona4": 130,
    }
    carrito = request.session.get("carrito", {})

    if not carrito:
        return redirect("pickup_food_en")

    total = 0

    for comida_id, cantidad in carrito.items():
        comida = get_object_or_404(Comida, id=comida_id)
        total += comida.precio * cantidad

    if request.method == 'POST':

        # 🔴 1. Obtener token del captcha
        token = request.POST.get('g-recaptcha-response')

        # 🔴 2. Validar captcha
        if not verificar_recaptcha(token):
            return HttpResponse("Captcha inválido, intentá nuevamente.")

        total = 0

        nombre = request.POST.get("nombre")
        email = request.POST.get("email")
        direccion = request.POST.get("direccion")
        tipo_pedido = request.POST.get("tipo_pedido")
        zona = request.POST.get("zona")
        forma_pago = request.POST.get("forma_pago")
        aclaraciones = request.POST.get("aclaraciones")

        pedido = Pedido.objects.create(
            nombre_cliente=nombre,
            email_cliente=email,
            direccion=direccion,
            tipo_pedido=tipo_pedido,
            forma_pago=forma_pago,
            total=0,
            zona=zona
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

        # 🚚 SHIPPING
        if tipo_pedido == "delivery":

            if not zona:
                return HttpResponse("Please select your delivery zone")

            if zona in ZONAS:
                total += ZONAS[zona]

        pedido.total = total
        pedido.save()

        request.session["carrito"] = {}

        if forma_pago == "efectivo":
            enviar_email_pedido(pedido)
            return redirect("order_success_en")

        return redirect("pagar_con_mercadopago", pedido_id=pedido.id)

    return render(request, "tienda/checkout_en.html", {
        "total": total,
    })
def order_success_en(request):
    return render(request, "tienda/order_success_en.html")

def verificar_recaptcha(token):
    data = {
        'secret': settings.RECAPTCHA_SECRET_KEY,
        'response': token
    }
    r = requests.post('https://www.google.com/recaptcha/api/siteverify', data=data)
    print("RESPUESTA CAPTCHA:", r.json())
    return r.json().get('success', False)