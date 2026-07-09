import math

LIMITE_CO = 35
LIMITE_MQ135 = 1200
LIMITE_PM = 35.4


def haversine_m(lat1, lng1, lat2, lng2):
    """Distancia en metros entre dos puntos GPS."""
    if None in (lat1, lng1, lat2, lng2):
        return 0.0
    R = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def calcular_centroide_y_radio(puntos):
    """
    puntos: lista de (lat, lng)
    Retorna (centro_lat, centro_lng, radio_metros, distancia_total_m)
    El centro es el promedio de todos los puntos (centroide), y el radio es la
    distancia máxima del centroide a cualquier punto del recorrido. Esto
    representa mejor el área cubierta que solo unir inicio-fin.
    """
    puntos_validos = [p for p in puntos if p[0] is not None and p[1] is not None]
    if not puntos_validos:
        return None, None, 0.0, 0.0

    centro_lat = sum(p[0] for p in puntos_validos) / len(puntos_validos)
    centro_lng = sum(p[1] for p in puntos_validos) / len(puntos_validos)

    radio = max(
        haversine_m(centro_lat, centro_lng, p[0], p[1]) for p in puntos_validos
    )
    # Radio mínimo de 15m para que el círculo sea visible aunque el recorrido
    # haya sido muy corto (ej. quedarse parado midiendo un solo punto).
    radio = max(radio, 15)

    distancia_total = 0.0
    for i in range(1, len(puntos_validos)):
        distancia_total += haversine_m(
            puntos_validos[i - 1][0], puntos_validos[i - 1][1],
            puntos_validos[i][0], puntos_validos[i][1],
        )

    return centro_lat, centro_lng, radio, distancia_total


def clasificar_nivel(promedio_co, promedio_mq135):
    """Devuelve el peor nivel entre los sensores (el más restrictivo manda)."""
    niveles_orden = {"bueno": 0, "moderado": 1, "malo": 2, "critico": 3, "sin datos": -1}

    def nivel_co(v):
        if v is None:
            return "sin datos"
        if v < 9:
            return "bueno"
        if v < 35:
            return "moderado"
        if v < 60:
            return "malo"
        return "critico"

    def nivel_mq135(v):
        if v is None:
            return "sin datos"
        if v < 800:
            return "bueno"
        if v < 1200:
            return "moderado"
        if v < 1500:
            return "malo"
        return "critico"

    niveles = [nivel_co(promedio_co), nivel_mq135(promedio_mq135)]
    niveles_validos = [n for n in niveles if n != "sin datos"]
    if not niveles_validos:
        return "sin datos", "#9ca3af"

    peor = max(niveles_validos, key=lambda n: niveles_orden[n])
    colores = {"bueno": "#22c55e", "moderado": "#f59e0b", "malo": "#ef4444", "critico": "#991b1b"}
    return peor, colores[peor]
