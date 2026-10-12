from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

# ⚠️ EDITAR ACÁ las fechas de cierre por vacaciones (ambas inclusive).
# Durante este rango no se toman pedidos online ni reservas para esas fechas.
VACACIONES_DESDE = date(2026, 10, 13)
VACACIONES_HASTA = date(2026, 10, 24)

# El servidor corre en UTC; el día "de hoy" se calcula en hora del restaurante.
ZONA_RESTAURANTE = ZoneInfo("America/Cancun")


def hoy_local():
    return datetime.now(ZONA_RESTAURANTE).date()


def fecha_en_vacaciones(fecha):
    return VACACIONES_DESDE <= fecha <= VACACIONES_HASTA


def pedidos_cerrados():
    return fecha_en_vacaciones(hoy_local())


def contexto(request):
    """Context processor: expone el estado de vacaciones a todos los templates."""

    hoy = hoy_local()

    return {
        "vacaciones_desde": VACACIONES_DESDE,
        "vacaciones_hasta": VACACIONES_HASTA,
        "vacaciones_vuelta": VACACIONES_HASTA + timedelta(days=1),
        # El aviso se muestra desde ya (para avisar antes) hasta el último día.
        "vacaciones_aviso": hoy <= VACACIONES_HASTA,
        "pedidos_cerrados": fecha_en_vacaciones(hoy),
    }
