"""Red lógica de calles del diseño M4, medida sobre piso.png (1920 x 1080 px) y
convertida al mundo OpenGL con ESCALA. Cada carril se divide en segmentos
(Carril); un vehículo avanza una distancia "s" sobre su segmento y luego pasa
al siguiente de su ruta, así nunca sale del asfalto."""

import math

# Conversión de pixeles de piso.png a unidades del mundo OpenGL
ESCALA = 3200.0 / 1920.0
# Unidades del mundo que equivalen a un metro (carril = 3.5 m, coche = 4 m)
M = 15.0

# Medidas tomadas de piso.png (en pixeles)
CENTRO_GLORIETA = (960.0, 540.0)
RADIO_GLORIETA = 95.0          # carril de circulación de la glorieta
ANGULO_ACCESO = 30.0           # separación angular entre salida y entrada de cada brazo
RADIO_EXTERIOR_GLORIETA = 132.0

# Línea central del circuito exterior (rectángulo con esquinas redondeadas)
ANILLO_U = (72.5, 1847.5)
ANILLO_V = (68.0, 1012.0)
RADIO_ESQUINA = 50.0
DESPLAZAMIENTO_CARRIL = 15.5   # distancia de cada carril a la línea central

RADIO_GIRO_T = 30.0            # radio de las vueltas a la derecha en las T

# Para cada lado del circuito: origen (punto medio, donde está la T),
# dirección de circulación e_t, normal hacia el interior de la ciudad e_n,
# media longitud del lado, desplazamiento de los carriles de la calle
# interior y distancia del origen al centro de la glorieta.
LADOS = {
    "N": dict(origen=(960.0, 68.0), e_t=(1.0, 0.0), e_n=(0.0, 1.0),
              media=837.5, w=24.5, ancho_calle=49.0, dist_glorieta=472.0, ang=90.0),
    "E": dict(origen=(1847.5, 540.0), e_t=(0.0, 1.0), e_n=(-1.0, 0.0),
              media=422.0, w=20.5, ancho_calle=40.5, dist_glorieta=887.5, ang=0.0),
    "S": dict(origen=(960.0, 1012.0), e_t=(-1.0, 0.0), e_n=(0.0, -1.0),
              media=837.5, w=24.5, ancho_calle=49.0, dist_glorieta=472.0, ang=270.0),
    "O": dict(origen=(72.5, 540.0), e_t=(0.0, -1.0), e_n=(1.0, 0.0),
              media=422.0, w=20.5, ancho_calle=40.5, dist_glorieta=887.5, ang=180.0),
}
ORDEN_LADOS = ["N", "E", "S", "O"]          # sentido horario del circuito
ORDEN_GLORIETA = ["E", "N", "O", "S"]       # sentido antihorario de la glorieta


# Funciones geométricas (puntos 2D en pixeles de la textura)
def punto_local(lado, t, n):
    """Convierte coordenadas locales (t a lo largo del circuito, n hacia el
    interior) de un lado del circuito a pixeles de la textura."""
    d = LADOS[lado]
    ox, oy = d["origen"]
    tx, ty = d["e_t"]
    nx, ny = d["e_n"]
    return (ox + t * tx + n * nx, oy + t * ty + n * ny)


def linea(p0, p1):
    return [p0, p1]


def arco(centro, radio, ang0, ang1, pasos=None):
    """Arco en coordenadas de la textura (v crece hacia abajo).
    Los ángulos se miden con atan2(dv, du) en grados."""
    if pasos is None:
        pasos = max(6, int(abs(ang1 - ang0) / 4))
    pts = []
    for i in range(pasos + 1):
        a = math.radians(ang0 + (ang1 - ang0) * i / pasos)
        pts.append((centro[0] + radio * math.cos(a), centro[1] + radio * math.sin(a)))
    return pts


def bezier(p0, d0, p3, d3, pasos=24):
    """Curva de Bézier cúbica que sale de p0 con dirección d0 y llega a p3
    con dirección d3. Se usa para entrar y salir de la glorieta con suavidad."""
    k = math.dist(p0, p3) * 0.45
    p1 = (p0[0] + d0[0] * k, p0[1] + d0[1] * k)
    p2 = (p3[0] - d3[0] * k, p3[1] - d3[1] * k)
    pts = []
    for i in range(pasos + 1):
        u = i / pasos
        a, b, c, e = (1 - u) ** 3, 3 * u * (1 - u) ** 2, 3 * u * u * (1 - u), u ** 3
        pts.append((a * p0[0] + b * p1[0] + c * p2[0] + e * p3[0],
                    a * p0[1] + b * p1[1] + c * p2[1] + e * p3[1]))
    return pts


def punto_glorieta(phi):
    """Punto del carril de la glorieta. phi se mide en sentido antihorario
    (visto desde arriba), con 0° hacia el este y 90° hacia el norte."""
    a = math.radians(phi)
    return (CENTRO_GLORIETA[0] + RADIO_GLORIETA * math.cos(a),
            CENTRO_GLORIETA[1] - RADIO_GLORIETA * math.sin(a))


def tangente_glorieta(phi):
    a = math.radians(phi)
    return (-math.sin(a), -math.cos(a))


def unir(*tramos):
    """Une listas de puntos evitando repetir el punto de unión."""
    pts = []
    for tramo in tramos:
        for p in tramo:
            if not pts or math.dist(pts[-1], p) > 1e-6:
                pts.append(p)
    return pts


class Carril:
    """Segmento de carril con una trayectoria (polilínea) en unidades del mundo."""

    def __init__(self, ident, puntos_px, tipo, vel_max):
        self.id = ident
        self.tipo = tipo              # recta, esquina, giro, calle, glorieta, entrada, salida
        self.puntos = [(x * ESCALA, z * ESCALA) for x, z in puntos_px]
        self.siguientes = []          # ids de los segmentos a los que se puede pasar
        self.alimentadores = []       # ids de los segmentos que desembocan aquí
        self.hermano = None           # carril paralelo del mismo sentido (cambio de carril)
        self.divergentes = []         # (segmento, s) que comparten el inicio con este
        self.interseccion = None      # nombre de la intersección que lo controla
        self.acceso = None            # acceso del semáforo que lo controla
        self.es_curva = tipo in ("esquina", "giro", "glorieta", "entrada", "salida")

        # Longitudes acumuladas y rumbos de cada tramo de la polilínea
        self.acum = [0.0]
        self.rumbos = []
        for (x0, z0), (x1, z1) in zip(self.puntos[:-1], self.puntos[1:]):
            self.acum.append(self.acum[-1] + math.hypot(x1 - x0, z1 - z0))
            self.rumbos.append(math.atan2(z1 - z0, x1 - x0))
        self.longitud = self.acum[-1]

        # Velocidad máxima: en curvas se limita por aceleración lateral (v = sqrt(a*R))
        radio_min = self._radio_minimo()
        if radio_min < float("inf"):
            vel_max = min(vel_max, math.sqrt(2.0 * M * radio_min))
        self.vel_max = vel_max

    def _radio_minimo(self):
        radio = float("inf")
        for i in range(1, len(self.rumbos)):
            dang = abs(normalizar_angulo(self.rumbos[i] - self.rumbos[i - 1]))
            ds = (self.acum[i + 1] - self.acum[i - 1]) / 2.0
            if dang > 1e-4:
                radio = min(radio, ds / dang)
        return radio

    def _indice(self, s):
        # Búsqueda binaria del tramo que contiene la distancia s
        lo, hi = 0, len(self.acum) - 2
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if self.acum[mid] <= s:
                lo = mid
            else:
                hi = mid - 1
        return lo

    def pose(self, s):
        """Regresa (x, z, rumbo) a una distancia s del inicio del segmento.
        El rumbo es el ángulo atan2(dz, dx) en radianes."""
        s = min(max(s, 0.0), self.longitud)
        i = self._indice(s)
        x0, z0 = self.puntos[i]
        x1, z1 = self.puntos[i + 1]
        largo = self.acum[i + 1] - self.acum[i]
        u = 0.0 if largo == 0 else (s - self.acum[i]) / largo
        # El rumbo se interpola entre tramos para que los giros se vean suaves
        r = self.rumbos[i]
        if u > 0.5 and i + 1 < len(self.rumbos):
            r = r + normalizar_angulo(self.rumbos[i + 1] - r) * (u - 0.5)
        elif u < 0.5 and i > 0:
            r = r + normalizar_angulo(self.rumbos[i - 1] - r) * (0.5 - u)
        return x0 + (x1 - x0) * u, z0 + (z1 - z0) * u, r


def normalizar_angulo(a):
    """Lleva un ángulo al intervalo (-pi, pi]."""
    while a <= -math.pi:
        a += 2 * math.pi
    while a > math.pi:
        a -= 2 * math.pi
    return a


class RedVial:
    """Construye todos los segmentos, sus conexiones y las intersecciones."""

    def __init__(self, vel_max=12.0 * M):
        self.vel_max = vel_max
        self.carriles = {}
        self.intersecciones = {}   # nombre -> dict con movimientos y accesos
        self.postes = []           # (interseccion, acceso, x, z) para dibujar semáforos
        self._construir_circuito()
        self._construir_calles_y_glorieta()
        for c in self.carriles.values():
            for sig in c.siguientes:
                self.carriles[sig].alimentadores.append(c.id)
        self._calcular_divergencias()

    def _calcular_divergencias(self):
        """Cuando dos segmentos salen del mismo punto (p. ej. seguir derecho o
        dar vuelta), al principio sus trayectorias siguen encimadas. Aquí se
        calcula hasta qué distancia "s" un coche en uno estorba al otro."""
        separacion = 2.2 * M
        for c in self.carriles.values():
            c.divergentes = []
        for c in self.carriles.values():
            for a in c.siguientes:
                for b in c.siguientes:
                    if a == b:
                        continue
                    ca, cb = self.carriles[a], self.carriles[b]
                    limite = min(ca.longitud, cb.longitud)
                    s = 0.0
                    while s < limite:
                        xa, za, _ = ca.pose(s)
                        xb, zb, _ = cb.pose(s)
                        if math.hypot(xa - xb, za - zb) > separacion:
                            break
                        s += 2.0
                    ca.divergentes.append((b, s))

    def _agregar(self, ident, puntos, tipo, siguientes=()):
        c = Carril(ident, puntos, tipo, self.vel_max)
        c.siguientes = list(siguientes)
        self.carriles[ident] = c
        return c

    def _poste(self, inter, acceso, punto_px):
        self.postes.append((inter, acceso, punto_px[0] * ESCALA, punto_px[1] * ESCALA))

    # Circuito exterior: dos carriles del mismo sentido (horario visto desde arriba)
    def _construir_circuito(self):
        carriles = {"int": DESPLAZAMIENTO_CARRIL, "ext": -DESPLAZAMIENTO_CARRIL}
        for i, lado in enumerate(ORDEN_LADOS):
            d = LADOS[lado]
            sig_lado = ORDEN_LADOS[(i + 1) % 4]
            L = d["media"]
            t_alto = self._medidas(lado)["t_alto"]
            t_sal = self._medidas(lado)["t_sal"]
            for nombre, n in carriles.items():
                base = f"{lado}_{nombre}"
                self._agregar(base + "_a", linea(punto_local(lado, -L, n), punto_local(lado, t_alto, n)),
                              "recta", [base + "_x"])
                self._agregar(base + "_x", linea(punto_local(lado, t_alto, n), punto_local(lado, t_sal, n)),
                              "recta", [base + "_b"])
                self._agregar(base + "_b", linea(punto_local(lado, t_sal, n), punto_local(lado, L, n)),
                              "recta", [base + "_esq"])
                # Esquina redondeada hacia el siguiente lado (arcos concéntricos)
                cx, cy = punto_local(lado, L, RADIO_ESQUINA)
                en = d["e_n"]
                a0 = math.degrees(math.atan2(-en[1], -en[0]))
                self._agregar(base + "_esq", arco((cx, cy), RADIO_ESQUINA - n, a0, a0 + 90.0),
                              "esquina", [f"{sig_lado}_{nombre}_a"])
            # Carriles paralelos donde se permite cambiar de carril
            for tramo in ("_a", "_b"):
                a = self.carriles[f"{lado}_int{tramo}"]
                b = self.carriles[f"{lado}_ext{tramo}"]
                a.hermano, b.hermano = b.id, a.id

    # Calles interiores de doble sentido, intersecciones en T y glorieta (antihoraria)
    def _medidas(self, lado):
        """Distancias locales (t, n) de un brazo, en pixeles de la textura."""
        w = LADOS[lado]["w"]
        n_calle = DESPLAZAMIENTO_CARRIL + RADIO_GIRO_T          # donde empieza la calle interior
        radio_borde = math.sqrt(RADIO_EXTERIOR_GLORIETA ** 2 - w ** 2)
        return dict(
            w=w,
            t_alto=-w - 40.0,                 # línea de alto del circuito antes de la T
            t_sal=w + 35.0,                   # fin de la zona de la T
            n_calle=n_calle,
            n_alto_calle=n_calle + 8.0,       # línea de alto de la calle hacia el circuito
            n_glorieta=LADOS[lado]["dist_glorieta"] - radio_borde - 10.0,   # línea de alto de la glorieta
        )

    def _construir_calles_y_glorieta(self):
        for lado in ORDEN_LADOS:
            self._construir_t(lado)
            self._construir_calles(lado)
            self._construir_arcos_glorieta(lado)
            self._registrar_intersecciones(lado)
        # Se marca qué intersección y acceso controla cada segmento de conexión
        for nombre, inter in self.intersecciones.items():
            for mov, info in inter["movimientos"].items():
                self.carriles[mov].interseccion = nombre
                self.carriles[mov].acceso = info["acceso"]

    def _construir_t(self, lado):
        """Vueltas a la derecha de la T: del circuito a la calle y de la calle al circuito."""
        d, m = LADOS[lado], self._medidas(lado)
        w, r, n_int = m["w"], RADIO_GIRO_T, DESPLAZAMIENTO_CARRIL
        e_t, e_n = d["e_t"], d["e_n"]

        # Del carril interior del circuito hacia la calle: recta corta + cuarto de círculo
        centro = punto_local(lado, -w - r, n_int + r)
        a0 = math.degrees(math.atan2(-e_n[1], -e_n[0]))
        giro = unir(linea(punto_local(lado, m["t_alto"], n_int), punto_local(lado, -w - r, n_int)),
                    arco(centro, r, a0, a0 + 90.0))
        self._agregar(f"T{lado}_gira", giro, "giro", [f"C{lado}_entra"])
        self.carriles[f"{lado}_int_a"].siguientes.append(f"T{lado}_gira")

        # De la calle al carril interior del circuito (incorporación)
        centro = punto_local(lado, w + r, n_int + r)
        a0 = math.degrees(math.atan2(-e_t[1], -e_t[0]))
        incorpora = unir(linea(punto_local(lado, w, m["n_alto_calle"]), punto_local(lado, w, m["n_calle"])),
                         arco(centro, r, a0, a0 + 90.0),
                         linea(punto_local(lado, w + r, n_int), punto_local(lado, m["t_sal"], n_int)))
        self._agregar(f"T{lado}_incorpora", incorpora, "giro", [f"{lado}_int_b"])

    def _construir_calles(self, lado):
        """Calle interior de ida y vuelta, entrada y salida de la glorieta."""
        d, m = LADOS[lado], self._medidas(lado)
        w, e_n = m["w"], d["e_n"]
        menos_n = (-e_n[0], -e_n[1])
        phi_entrada = d["ang"] + ANGULO_ACCESO
        phi_salida = d["ang"] - ANGULO_ACCESO
        inicio_entrada = punto_local(lado, -w, m["n_glorieta"])
        fin_salida = punto_local(lado, w, m["n_glorieta"])

        self._agregar(f"C{lado}_entra", linea(punto_local(lado, -w, m["n_calle"]), inicio_entrada),
                      "calle", [f"G{lado}_entrada"])
        self._agregar(f"G{lado}_entrada",
                      bezier(inicio_entrada, e_n, punto_glorieta(phi_entrada), tangente_glorieta(phi_entrada)),
                      "entrada", [f"G{lado}_sig"])
        self._agregar(f"G{lado}_salida",
                      bezier(punto_glorieta(phi_salida), tangente_glorieta(phi_salida), fin_salida, menos_n),
                      "salida", [f"C{lado}_sale"])
        self._agregar(f"C{lado}_sale", linea(fin_salida, punto_local(lado, w, m["n_alto_calle"])),
                      "calle", [f"T{lado}_incorpora"])

    def _construir_arcos_glorieta(self, lado):
        """'paso' pasa frente al brazo (de la salida a la entrada); 'sig' va al siguiente brazo."""
        phi0 = LADOS[lado]["ang"]
        k = ORDEN_GLORIETA.index(lado)
        sig = ORDEN_GLORIETA[(k + 1) % 4]
        self._agregar(f"G{lado}_paso", self._arco_glorieta(phi0 - ANGULO_ACCESO, phi0 + ANGULO_ACCESO),
                      "glorieta", [f"G{lado}_sig"])
        self._agregar(f"G{lado}_sig", self._arco_glorieta(phi0 + ANGULO_ACCESO, phi0 + 90.0 - ANGULO_ACCESO),
                      "glorieta", [f"G{sig}_paso", f"G{sig}_salida"])

    def _registrar_intersecciones(self, lado):
        """Intersección en T y acceso a la glorieta del brazo, con sus postes."""
        d, m = LADOS[lado], self._medidas(lado)
        n_int = DESPLAZAMIENTO_CARRIL
        # T: el semáforo alterna el acceso del circuito y el de la calle. La
        # incorporación choca con quien sigue derecho por el carril interior.
        self.intersecciones[f"T{lado}"] = dict(
            tipo="T",
            accesos=["circuito", "calle"],
            movimientos={
                f"{lado}_int_x": dict(acceso="circuito", conflictos=[f"T{lado}_incorpora"]),
                f"{lado}_ext_x": dict(acceso="circuito", conflictos=[]),
                f"T{lado}_gira": dict(acceso="circuito", conflictos=[]),
                f"T{lado}_incorpora": dict(acceso="calle", conflictos=[f"{lado}_int_x"]),
            },
            aproximaciones={"circuito": [f"{lado}_int_a", f"{lado}_ext_a"], "calle": [f"C{lado}_sale"]},
        )
        self._poste(f"T{lado}", "circuito", punto_local(lado, m["t_alto"], n_int + 22.0))
        self._poste(f"T{lado}", "calle", punto_local(lado, d["ancho_calle"] + 6.0, m["n_alto_calle"]))

        # Glorieta: el semáforo solo controla la entrada; quien circula tiene prioridad
        self.intersecciones[f"G{lado}"] = dict(
            tipo="glorieta",
            accesos=["entrada", "glorieta"],
            movimientos={f"G{lado}_entrada": dict(acceso="entrada", conflictos=[])},
            aproximaciones={"entrada": [f"C{lado}_entra"], "glorieta": [f"G{lado}_paso"]},
        )
        self._poste(f"G{lado}", "entrada", punto_local(lado, -d["ancho_calle"] - 6.0, m["n_glorieta"]))

    def _arco_glorieta(self, phi0, phi1):
        pasos = max(6, int((phi1 - phi0) / 3))
        return [punto_glorieta(phi0 + (phi1 - phi0) * i / pasos) for i in range(pasos + 1)]

    def segmentos_glorieta(self):
        return [c.id for c in self.carriles.values() if c.tipo in ("glorieta", "entrada")]
