"""Sistema multiagentes de tráfico con AgentPy: vehículos, semáforos e
intersecciones. Lo usan main.py (con gráficos) y Simulacion.ipynb (sin ventana).
Unidades internas: unidades del mundo OpenGL (M por metro) y segundos."""

import math
import agentpy as ap
import pandas as pd

from red_vial import RedVial, M, normalizar_angulo

# Parámetros físicos (en unidades del mundo; M = unidades por metro)
DT = 0.1                    # paso lógico fijo [s]
LARGO = 4.0 * M             # largo del coche
ANCHO = 1.6 * M             # ancho del coche
DIAGONAL = math.hypot(LARGO, ANCHO)
DIST_EJES = 34.8            # distancia entre ejes del modelo 3D (escala 6)
RADIO_LLANTA = 4.3          # radio de la llanta del modelo 3D (escala 6)
V_MAX = 12.0 * M            # velocidad máxima en recta (43 km/h)
A_MAX = 2.0 * M             # aceleración máxima
B_COMODO = 3.0 * M          # frenado cómodo
B_MAX = 8.0 * M             # frenado de emergencia
S0 = 2.0 * M                # distancia mínima con el vehículo de enfrente
T_SEGURIDAD = 1.2           # tiempo de separación deseado [s]
DIST_CAMBIO = 14.0 * M      # distancia que se recorre al cambiar de carril
ALCANCE = 70.0 * M          # distancia a la que un vehículo "ve" hacia adelante
V_DETENIDO = 0.5 * M        # por debajo de esta velocidad el coche está detenido
DETECCION = 45.0 * M        # zona de detección de cada acceso del semáforo
CAPACIDAD_GLORIETA = 7      # vehículos máximos dentro de la glorieta
T_HUECO_GLORIETA = 3.0      # hueco mínimo [s] para entrar a la glorieta

# Tiempos de los semáforos [s]
T_AMARILLO = 3.0
T_TODO_ROJO = 1.5
VERDE_FIJO = {"circuito": 15.0, "calle": 10.0, "entrada": 10.0, "glorieta": 10.0}
# Control adaptativo:
VERDE_MIN = 5.0             # el verde dura al menos esto antes de poder cambiar
VERDE_MAX = 25.0            # al llegar aquí cambia si el otro acceso tiene coches; si nadie espera, el verde sigue
ESPERA_TOLERADA = 30.0      # si un coche lleva esto detenido en el otro acceso, se pide el cambio de fase
                            # (es un umbral para cambiar, no una espera máxima garantizada)

# Transiciones permitidas de la máquina de estados del vehículo.
# Un cambio de carril se interrumpe con DESACELERAR o ESPERAR si aparece un
# obstáculo y vuelve a CAMBIAR_CARRIL al reanudar la marcha.
TRANSICIONES = {
    "AVANZAR": {"DESACELERAR", "GIRAR", "CAMBIAR_CARRIL", "ESPERAR"},
    "DESACELERAR": {"AVANZAR", "ESPERAR", "GIRAR", "CAMBIAR_CARRIL"},
    "ESPERAR": {"AVANZAR", "DESACELERAR", "GIRAR", "CAMBIAR_CARRIL"},
    "GIRAR": {"AVANZAR", "DESACELERAR", "ESPERAR"},
    "CAMBIAR_CARRIL": {"AVANZAR", "DESACELERAR", "ESPERAR"},
}


class AgenteVehiculo(ap.Agent):

    def setup(self, carril, s):
        red = self.model.red
        self.carril = carril                  # id del segmento actual
        self.s = s                            # distancia recorrida en el segmento
        self.velocidad = 0.0
        self.aceleracion = 0.0
        self.estado = "AVANZAR"
        self.ruta = []                        # próximos segmentos a recorrer
        self.permiso = None                   # movimiento autorizado por una intersección
        self.distancia_seguridad = S0
        self.tiempo_espera = 0.0              # tiempo total detenido [s]
        self.espera_actual = 0.0              # tiempo detenido sin moverse [s]
        self.espera_maxima = 0.0
        self.prioridad = 0                    # 0 = circulando con prioridad
        self.vueltas_glorieta = 0
        self.cambio = None                    # datos del cambio de carril en curso
        self.por_liberar = None               # cruce que todavía ocupa la cola del coche
        x, z, r = red.carriles[carril].pose(s)
        self.posicion = (x, z)
        self.direccion = r                    # rumbo en radianes, atan2(dz, dx)
        self.pos_anterior = self.posicion
        self.dir_anterior = r
        self.giro_llantas = 0.0               # ángulo del volante [grados]
        self.rotacion_llantas = 0.0           # giro acumulado de las llantas [grados]
        self.planificar()

    def _opciones(self, seg_id, permitir_cambio, vueltas):
        """Opciones (segmento, peso) al terminar seg_id, respetando sentidos."""
        red = self.model.red
        seg = red.carriles[seg_id]
        opciones = []
        for sig in seg.siguientes:
            peso = 1.0
            if sig.startswith("T") and sig.endswith("_gira"):
                peso = 0.7                                  # dar vuelta hacia la glorieta
            elif sig.endswith("_salida"):
                peso = 2.0 if vueltas >= 1 else 0.6         # salir de la glorieta
                if vueltas >= 3:
                    peso = 100.0
            elif sig.endswith("_paso") and vueltas >= 3:
                peso = 0.01
            opciones.append((sig, peso))
        if permitir_cambio and seg.hermano:
            peso = {"_ext_a": 0.8, "_int_a": 0.15, "_int_b": 0.35, "_ext_b": 0.2}
            for k, p in peso.items():
                if seg_id.endswith(k):
                    opciones.append((seg.hermano, p))
        return opciones

    def planificar(self, excluir=None):
        """Completa la ruta con elecciones aleatorias (reproducibles por semilla)."""
        red = self.model.red
        actual = self.ruta[-1] if self.ruta else self.carril
        anterior = self.ruta[-2] if len(self.ruta) >= 2 else self.carril
        vueltas = self.vueltas_glorieta
        while len(self.ruta) < 6:
            vino_de_cambio = red.carriles[actual].hermano == anterior and anterior != actual
            ya_cambio = self.cambio is not None and not self.ruta
            opciones = self._opciones(actual, not vino_de_cambio and not ya_cambio, vueltas)
            nombres = []
            pesos = []
            for nombre, peso in opciones:
                if nombre != excluir or len(opciones) == 1:
                    nombres.append(nombre)
                    pesos.append(peso)
            excluir = None          # solo se excluye en la primera elección
            elegido = self.model.random.choices(nombres, weights=pesos)[0]
            if elegido.endswith("_sig"):
                vueltas += 1
            if elegido.endswith("_salida"):
                vueltas = 0
            anterior, actual = actual, elegido
            self.ruta.append(elegido)

    def replanificar(self, excluir):
        self.ruta = []
        self.planificar(excluir)
        self._cancelar_permiso()

    def _cancelar_permiso(self):
        """Si la ruta cambió y ya no pasará por el movimiento autorizado,
        avisa a la intersección para liberar la zona de conflicto."""
        if (self.permiso and self.carril != self.permiso and self.permiso not in self.ruta[:1]
                and self.permiso != self.por_liberar):
            inter = self.model.inter[self.model.red.carriles[self.permiso].interseccion]
            inter.cancelar(self, self.permiso)

    def _siguiente_controlado(self):
        """Primer segmento controlado por intersección dentro del alcance."""
        red = self.model.red
        dist = red.carriles[self.carril].longitud - self.s
        for seg_id in self.ruta:
            if seg_id == red.carriles[self.carril].hermano:
                continue
            seg = red.carriles[seg_id]
            if seg.interseccion:
                return seg_id, dist
            dist += seg.longitud
            if dist > ALCANCE:
                break
        return None, None

    def percibir(self):
        """Revisa salidas bloqueadas y envía solicitudes de paso."""
        red = self.model.red
        if not self.ruta:
            self.planificar()
        actual = red.carriles[self.carril]
        prox = self.ruta[0]
        # Si la salida de la glorieta o la vuelta hacia la calle están llenas,
        # se cambia la ruta para no bloquear a los demás.
        if prox != actual.hermano and (prox.endswith("_salida") or prox.endswith("_gira")):
            dist = actual.longitud - self.s
            destino = red.carriles[prox].siguientes[0]
            if dist < 25.0 * M and not self.model.hay_espacio(destino, ignorar=self) and self.permiso != prox:
                self.replanificar(excluir=prox)
        mov, dist = self._siguiente_controlado()
        if mov and self.permiso != mov:
            dist_frente = dist - LARGO / 2
            alcance = max(18.0 * M, self.velocidad ** 2 / (2 * B_COMODO) + 12.0 * M)
            if dist_frente < alcance:
                inter = self.model.inter[red.carriles[mov].interseccion]
                inter.recibir_solicitud(self, mov, dist_frente)

    def puede_frenar(self, dist_frente):
        return dist_frente >= self.velocidad ** 2 / (2 * B_COMODO) - 0.5 * M

    def _idm(self, v0, brecha, v_lider):
        """Modelo de conductor inteligente (IDM) para la aceleración."""
        v = self.velocidad
        a = A_MAX * (1 - (v / max(v0, 0.1)) ** 4)
        if brecha is not None:
            dv = v - v_lider
            s_estrella = S0 + max(0.0, v * T_SEGURIDAD + v * dv / (2 * math.sqrt(A_MAX * B_COMODO)))
            a -= A_MAX * (s_estrella / max(brecha, 0.1)) ** 2
        return a

    def _coches_en(self, seg, es_actual):
        """Lista (s, vehículo) de los coches que ocupan el segmento 'seg'."""
        ocup = self.model.ocupacion
        coches = list(ocup.get(seg.id, []))
        if es_actual and self.cambio:
            coches += ocup.get(self.cambio["origen"], [])
        # Coches que cambian de carril hacia este segmento o desde él
        coches += self.model.cambiando.get(seg.id, [])
        coches += self.model.origen_cambio.get(seg.id, [])
        # Coches que acaban de tomar otra rama desde el mismo punto: al
        # principio sus trayectorias siguen encimadas con este segmento
        for otro_seg, s_separacion in seg.divergentes:
            for s_o, otro in ocup.get(otro_seg, []):
                if s_o < s_separacion + LARGO / 2:
                    coches.append((s_o, otro))
        return coches

    def _coches_que_se_unen(self, seg, previo):
        """Coches que llegan al inicio de 'seg' por otra rama (unión).
        Se regresan con s negativa, como si ya estuvieran en 'seg'."""
        red = self.model.red
        coches = []
        for f in seg.alimentadores:
            if f == previo:
                continue
            for s_o, otro in self.model.ocupacion.get(f, []):
                if otro.ruta and otro.ruta[0] == seg.id:
                    falta = red.carriles[f].longitud - s_o
                    coches.append((-falta, otro))
        return coches

    def _buscar_obstaculo(self):
        """Regresa (brecha, velocidad) del obstáculo más cercano: otro coche,
        la línea de alto sin permiso o un coche que llega a la misma unión."""
        red = self.model.red
        segmentos = [self.carril]
        for r in self.ruta:
            if r != red.carriles[self.carril].hermano:
                segmentos.append(r)
        inicio = -self.s           # distancia desde mi posición al inicio de cada segmento
        previo = None
        for i, seg_id in enumerate(segmentos):
            seg = red.carriles[seg_id]
            # Línea de alto: sin permiso, el coche se detiene antes del cruce
            if i > 0 and seg.interseccion and self.permiso != seg_id:
                return inicio - LARGO / 2 + S0 * 0.5, 0.0
            coches = self._coches_en(seg, i == 0)
            if i > 0:
                coches += self._coches_que_se_unen(seg, previo)
            lider = None
            for s_o, otro in coches:
                if otro is self:
                    continue
                d = inicio + s_o
                # Empate en una unión: pasa primero el de mayor prioridad (o menor id)
                gana_otro = d == 0 and (otro.prioridad, otro.id) < (self.prioridad, self.id)
                if (d > 0 or gana_otro) and (lider is None or d < lider[0]):
                    lider = (d, otro.velocidad)
            if lider is not None:
                return lider[0] - LARGO, lider[1]
            inicio += seg.longitud
            previo = seg_id
            if inicio > ALCANCE:
                break
        return None, 0.0

    def _velocidad_permitida(self):
        """Velocidad máxima considerando las curvas que vienen adelante."""
        red = self.model.red
        actual = red.carriles[self.carril]
        v = actual.vel_max
        dist = actual.longitud - self.s
        for seg_id in self.ruta:
            seg = red.carriles[seg_id]
            if seg_id == actual.hermano:
                continue
            v = min(v, math.sqrt(seg.vel_max ** 2 + 2 * B_COMODO * 0.6 * max(dist, 0.0)))
            dist += seg.longitud
            if dist > ALCANCE:
                break
        return v

    def _intentar_cambio(self):
        """Cambio de carril si el siguiente paso de la ruta es el carril paralelo."""
        red = self.model.red
        actual = red.carriles[self.carril]
        if self.cambio or not self.ruta or self.ruta[0] != actual.hermano:
            return
        restante = actual.longitud - self.s
        if restante < DIST_CAMBIO + LARGO:
            self.replanificar(excluir=actual.hermano)     # ya no hay espacio: se cancela
            return
        destino = red.carriles[actual.hermano]
        vecinos = (self.model.ocupacion.get(destino.id, []) + self.model.cambiando.get(destino.id, [])
                   + self.model.origen_cambio.get(destino.id, []))
        # Coches que vienen detrás en el segmento anterior del carril destino
        for f in destino.alimentadores:
            largo_f = red.carriles[f].longitud
            vecinos += [(s_o - largo_f, o) for s_o, o in self.model.ocupacion.get(f, ())]
        for s_o, otro in vecinos:
            if s_o >= self.s:
                hueco = s_o - self.s - LARGO
                if hueco < S0 + self.velocidad * 0.8:
                    return
            else:
                hueco = self.s - s_o - LARGO
                if hueco < S0 + otro.velocidad * 1.0:
                    return
        # Se inicia el cambio: el vehículo pasa lógicamente al carril destino
        xo, zo, _ = actual.pose(self.s)
        xd, zd, _ = destino.pose(self.s)
        self.cambio = {"origen": actual.id, "offset": (xo - xd, zo - zd), "avance": 0.0}
        self.model.cambiando.setdefault(destino.id, []).append((self.s, self))
        self.model.origen_cambio.setdefault(actual.id, []).append((self.s, self))
        self.carril = destino.id
        self.ruta.pop(0)
        self.model.contadores["cambios_carril"] += 1
        self._cancelar_permiso()

    def decidir(self):
        self._intentar_cambio()
        brecha, v_lider = self._buscar_obstaculo()
        a = self._idm(self._velocidad_permitida(), brecha, v_lider)
        self.aceleracion = max(-B_MAX, min(A_MAX, a))
        self.distancia_seguridad = S0 + self.velocidad * T_SEGURIDAD

    def mover(self):
        red = self.model.red
        v0 = self.velocidad
        v1 = max(0.0, v0 + self.aceleracion * DT)
        ds = (v0 + v1) / 2 * DT
        self.velocidad = v1
        self.pos_anterior = self.posicion
        self.dir_anterior = self.direccion

        # Revisión de la línea de alto (frente del coche) antes de avanzar
        seg = red.carriles[self.carril]
        frente_antes = seg.longitud - self.s - LARGO / 2
        frente_despues = frente_antes - ds
        if self.ruta and frente_antes >= 0 > frente_despues:
            prox = red.carriles[self.ruta[0]]
            if prox.interseccion and self.ruta[0] != seg.hermano:
                inter = self.model.inter[prox.interseccion]
                if self.permiso != prox.id or inter.semaforo.luz(prox.acceso) == "ROJO":
                    self.model.contadores["infracciones"] += 1

        self.s += ds
        if self.cambio:
            self.cambio["avance"] += ds
        while self.s > red.carriles[self.carril].longitud:
            self.s -= red.carriles[self.carril].longitud
            self._entrar_siguiente()
        # El cruce se libera cuando la cola del coche (LARGO/2 detrás del centro) ya salió
        if self.por_liberar and self.s >= LARGO / 2:
            self._liberar_cruce()

        # Pose final: se aplica el desplazamiento lateral si cambia de carril
        seg = red.carriles[self.carril]
        x, z, r = seg.pose(self.s)
        if self.cambio:
            p = min(1.0, self.cambio["avance"] / DIST_CAMBIO)
            g = 3 * p * p - 2 * p ** 3
            dg = (6 * p - 6 * p * p) / DIST_CAMBIO
            ox, oz = self.cambio["offset"]
            x += ox * (1 - g)
            z += oz * (1 - g)
            r = math.atan2(math.sin(r) - oz * dg, math.cos(r) - ox * dg)
            if p >= 1.0:
                self.cambio = None
        self.posicion = (x, z)
        self.direccion = r

        # Llantas: giro del volante según la curvatura y rotación por distancia
        if ds > 1e-3:
            curvatura = -normalizar_angulo(r - self.dir_anterior) / ds
            objetivo = math.degrees(math.atan(DIST_EJES * curvatura))
            objetivo = max(-35.0, min(35.0, objetivo))
            self.giro_llantas += (objetivo - self.giro_llantas) * 0.5
            self.rotacion_llantas = (self.rotacion_llantas - math.degrees(ds / RADIO_LLANTA)) % 360.0

        # Tiempo de espera
        if self.velocidad < V_DETENIDO:
            self.tiempo_espera += DT
            self.espera_actual += DT
            self.espera_maxima = max(self.espera_maxima, self.espera_actual)
        else:
            self.espera_actual = 0.0
        self._actualizar_estado()

    def _entrar_siguiente(self):
        red = self.model.red
        anterior = red.carriles[self.carril]
        if not self.ruta:
            self.planificar()
        nuevo = self.ruta.pop(0)
        if nuevo == anterior.hermano:          # no debería pasar: se omite el cambio
            nuevo = self.ruta.pop(0) if self.ruta else anterior.siguientes[0]
        if self.por_liberar:                   # entró a otro segmento antes de liberar
            self._liberar_cruce()
        if anterior.interseccion:              # el centro salió; falta que salga la cola
            self.por_liberar = anterior.id
        self.carril = nuevo
        self.cambio = None
        seg = red.carriles[nuevo]
        if seg.tipo in ("glorieta", "entrada"):
            self.prioridad = 0 if seg.tipo == "glorieta" else 1
            if nuevo.endswith("_sig"):
                self.vueltas_glorieta += 1
        else:
            self.prioridad = 0 if seg.tipo in ("recta", "esquina") else 1
            self.vueltas_glorieta = 0
        self.planificar()

    def _liberar_cruce(self):
        inter = self.model.inter[self.model.red.carriles[self.por_liberar].interseccion]
        inter.liberar(self, self.por_liberar)
        self.por_liberar = None

    def _actualizar_estado(self):
        """Máquina de estados: decide el nuevo estado según las condiciones."""
        seg = self.model.red.carriles[self.carril]
        if self.velocidad < V_DETENIDO and self.aceleracion <= 0.05 * M:
            nuevo = "ESPERAR"
        elif self.aceleracion < -0.5 * M and (self.cambio or not seg.es_curva):
            nuevo = "DESACELERAR"
        elif self.cambio:
            nuevo = "CAMBIAR_CARRIL"
        elif seg.es_curva:
            nuevo = "GIRAR" if self.aceleracion > -1.0 * M else "DESACELERAR"
        else:
            nuevo = "AVANZAR"
        if nuevo != self.estado and nuevo not in TRANSICIONES[self.estado]:
            nuevo = "AVANZAR"      # paso intermedio (no ocurre con la tabla actual)
        if nuevo != self.estado:
            clave = self.estado + "->" + nuevo
            self.model.transiciones[clave] = self.model.transiciones.get(clave, 0) + 1
            self.estado = nuevo


class AgenteSemaforo(ap.Agent):

    def setup(self, nombre, accesos, fase_inicial=0):
        self.nombre = nombre
        self.accesos = accesos            # una fase verde por acceso
        self.fase = fase_inicial
        self.estado = "VERDE"             # VERDE, AMARILLO o TODO_ROJO
        self.tiempo = 0.0
        self.interseccion = None

    def luz(self, acceso):
        """Color que ve un acceso: VERDE, AMARILLO o ROJO."""
        if self.estado == "TODO_ROJO" or self.accesos[self.fase] != acceso:
            return "ROJO"
        return self.estado

    def _terminar_verde(self):
        acceso = self.accesos[self.fase]
        otro = self.accesos[(self.fase + 1) % len(self.accesos)]
        if self.model.p.politica == "fija":
            return self.tiempo >= VERDE_FIJO[acceso]
        # Control adaptativo: usa la demanda que mide la intersección
        dem = self.interseccion.demanda
        cola_actual, cola_otra = dem[acceso]["vehiculos"], dem[otro]["vehiculos"]
        espera_otra = dem[otro]["espera_max"]
        if self.tiempo < VERDE_MIN:
            return False
        if cola_otra == 0:
            return False                      # nadie espera: se mantiene el verde
        if cola_actual == 0:
            return True                       # el acceso en verde ya está vacío
        if espera_otra >= ESPERA_TOLERADA:
            return True                       # alguien lleva mucho tiempo detenido en el otro acceso
        return self.tiempo >= VERDE_MAX

    def actualizar(self):
        self.tiempo += DT
        if self.estado == "VERDE" and self._terminar_verde():
            self.estado, self.tiempo = "AMARILLO", 0.0
        elif self.estado == "AMARILLO" and self.tiempo >= T_AMARILLO:
            self.estado, self.tiempo = "TODO_ROJO", 0.0
        elif self.estado == "TODO_ROJO" and self.tiempo >= T_TODO_ROJO:
            self.fase = (self.fase + 1) % len(self.accesos)
            self.estado, self.tiempo = "VERDE", 0.0


class AgenteInterseccion(ap.Agent):

    def setup(self, nombre, datos, semaforo):
        self.nombre = nombre
        self.tipo = datos["tipo"]
        self.movimientos = datos["movimientos"]
        self.aproximaciones = datos["aproximaciones"]
        self.semaforo = semaforo
        semaforo.interseccion = self
        self.solicitudes = []
        self.ocupacion = {m: set() for m in self.movimientos}
        self.cruces = 0
        self.demanda = {a: {"vehiculos": 0, "detenidos": 0, "espera_max": 0.0} for a in datos["accesos"]}

    def recibir_solicitud(self, vehiculo, movimiento, distancia):
        self.solicitudes.append((distancia, vehiculo.id, vehiculo, movimiento))

    def cancelar(self, vehiculo, movimiento):
        self.ocupacion[movimiento].discard(vehiculo)
        if vehiculo.permiso == movimiento:
            vehiculo.permiso = None
        self.model.mensaje(vehiculo.id, self.nombre, "CANCELA", movimiento)

    def liberar(self, vehiculo, movimiento):
        self.ocupacion[movimiento].discard(vehiculo)
        if vehiculo.permiso == movimiento:
            vehiculo.permiso = None
        self.cruces += 1
        self.model.mensaje(vehiculo.id, self.nombre, "LIBERA", movimiento)

    def _motivo_rechazo(self, veh, mov, dist):
        info = self.movimientos[mov]
        luz = self.semaforo.luz(info["acceso"])
        if luz == "ROJO":
            return "semaforo en rojo"
        if luz == "AMARILLO" and veh.puede_frenar(dist):
            return "amarillo, puede frenar"
        for c in info["conflictos"]:
            if self.ocupacion[c]:
                return f"conflicto con {c}"
        red = self.model.red
        destino = red.carriles[mov].siguientes[0]
        comprometidos = sum(1 for o in self.ocupacion[mov] if o.carril != destino)
        if not self.model.hay_espacio(destino, extra=comprometidos, ignorar=veh):
            return "sin espacio a la salida"
        if self.tipo == "glorieta":
            if self.model.vehiculos_en_glorieta() >= CAPACIDAD_GLORIETA:
                return "glorieta llena"
            if not self._hueco_glorieta():
                return "prioridad de la glorieta"
        return None

    def _hueco_glorieta(self):
        """Prioridad a quien ya circula: busca un hueco antes del punto de unión."""
        red = self.model.red
        lado = self.nombre[1:]
        paso = red.carriles[f"G{lado}_paso"]
        previo = paso.alimentadores[0]
        for seg_id, extra in ((paso.id, 0.0), (previo, paso.longitud)):
            seg = red.carriles[seg_id]
            for s_o, otro in self.model.ocupacion.get(seg_id, ()):
                if seg_id == previo and otro.ruta and otro.ruta[0] != paso.id:
                    continue                     # va a salir antes de la unión
                dist = seg.longitud - s_o + extra
                if dist < max(1.5 * LARGO, otro.velocidad * T_HUECO_GLORIETA + LARGO):
                    return False
        return True

    def resolver(self):
        # 0) Limpieza defensiva: permisos de vehículos que ya no van a cruzar
        for mov, vehiculos in self.ocupacion.items():
            for veh in list(vehiculos):
                if veh.carril != mov and veh.permiso != mov and veh.por_liberar != mov:
                    vehiculos.discard(veh)
        # 1) Si la luz dejó de estar en verde se retiran los permisos de quien aún puede frenar
        for mov, vehiculos in self.ocupacion.items():
            if self.semaforo.luz(self.movimientos[mov]["acceso"]) == "VERDE":
                continue
            for veh in list(vehiculos):
                if veh.carril != mov:
                    seg = self.model.red.carriles[veh.carril]
                    dist = seg.longitud - veh.s - LARGO / 2
                    if veh.ruta and veh.ruta[0] == mov and dist > 0 and veh.puede_frenar(dist):
                        vehiculos.discard(veh)
                        veh.permiso = None
                        self.model.mensaje(self.nombre, veh.id, "REVOCA", mov)
        # 2) Solicitudes en orden: el más cercano a la línea primero
        # (distancia, id) nunca se repiten, así que basta con ordenar las tuplas
        for dist, _, veh, mov in sorted(self.solicitudes):
            motivo = self._motivo_rechazo(veh, mov, dist)
            self.model.mensaje(veh.id, self.nombre, "SOLICITA", mov)
            if motivo is None:
                veh.permiso = mov
                self.ocupacion[mov].add(veh)
                self.model.mensaje(self.nombre, veh.id, "PERMISO", mov)
            else:
                self.model.mensaje(self.nombre, veh.id, "RECHAZO", f"{mov}: {motivo}")
        self.solicitudes.clear()

    def medir(self):
        """Mide la demanda de cada acceso (la usa el semáforo adaptativo)."""
        red = self.model.red
        for acceso, segs in self.aproximaciones.items():
            veh = det = 0
            espera = 0.0
            for seg_id in segs:
                seg = red.carriles[seg_id]
                for s_o, otro in self.model.ocupacion.get(seg_id, ()):
                    if seg.longitud - s_o < DETECCION:
                        veh += 1
                        if otro.velocidad < V_DETENIDO:
                            det += 1
                            espera = max(espera, otro.espera_actual)
            self.demanda[acceso] = {"vehiculos": veh, "detenidos": det, "espera_max": espera}


class ModeloTrafico(ap.Model):
    """Parámetros (self.p): n_vehiculos, politica ('fija' o 'adaptativa'),
    steps (pasos de DT segundos) y seed."""

    def setup(self):
        self.red = RedVial(V_MAX)
        self.contadores = {"infracciones": 0, "colisiones": 0, "cambios_carril": 0,
                           "SOLICITA": 0, "PERMISO": 0, "RECHAZO": 0, "REVOCA": 0,
                           "LIBERA": 0, "CANCELA": 0}
        self.transiciones = {}          # conteo de cambios de estado de los vehículos
        self.registro_mensajes = []
        self.ocupacion = {}
        self.cambiando = {}
        self.origen_cambio = {}
        self._pares_en_choque = set()
        self.tiempo = 0.0

        # Semáforos e intersecciones (8, como en el diseño M4)
        semaforos, intersecciones = [], []
        for nombre, datos in self.red.intersecciones.items():
            # Desfase inicial: los accesos E y O de la glorieta empiezan en rojo
            fase = 1 if nombre in ("GE", "GO") else 0
            sem = AgenteSemaforo(self, nombre=nombre, accesos=datos["accesos"], fase_inicial=fase)
            semaforos.append(sem)
            intersecciones.append(AgenteInterseccion(self, nombre=nombre, datos=datos, semaforo=sem))
        self.semaforos = ap.AgentList(self, semaforos)
        self.intersecciones = ap.AgentList(self, intersecciones)
        self.inter = {i.nombre: i for i in self.intersecciones}

        # Vehículos en posiciones distintas sobre carriles rectos y calles
        self.vehiculos = ap.AgentList(self, [])
        for carril, s in self._posiciones_iniciales(self.p.n_vehiculos):
            self.vehiculos.append(AgenteVehiculo(self, carril=carril, s=s))
        self._actualizar_ocupacion()
        self.accesos_controlados = [(i, a) for i in self.intersecciones for a in i.aproximaciones
                                    if a != "glorieta"]
        self.suma_velocidad = 0.0
        self.suma_fila = 0.0
        self.fila_maxima = 0
        self.muestras = 0

    def _posiciones_iniciales(self, n):
        """Posiciones al azar en rectas y calles (no en cruces), sin encimarse."""
        candidatos = []
        pesos = []
        for c in self.red.carriles.values():
            if (c.tipo == "recta" and not c.id.endswith("_x")) or c.tipo == "calle":
                candidatos.append(c)
                pesos.append(c.longitud - 3 * LARGO)    # carriles largos reciben más coches
        posiciones = []
        puntos = []
        intentos = 0
        while len(posiciones) < n:
            intentos += 1
            if intentos > 20000:
                raise ValueError(f"No caben {n} vehículos sin encimarse")
            c = self.random.choices(candidatos, weights=pesos)[0]
            s = self.random.uniform(1.5 * LARGO, c.longitud - 1.5 * LARGO)
            x, z, _ = c.pose(s)
            libre = True
            for x2, z2 in puntos:
                if math.hypot(x - x2, z - z2) <= LARGO + 2 * S0:
                    libre = False
            if libre:
                posiciones.append((c.id, s))
                puntos.append((x, z))
        return posiciones

    def _actualizar_ocupacion(self):
        ocup = {}
        for v in self.vehiculos:
            ocup.setdefault(v.carril, []).append((v.s, v))
        for lista in ocup.values():
            lista.sort(key=lambda x: (x[0], x[1].id))
        self.ocupacion = ocup
        self.cambiando = {}
        self.origen_cambio = {}
        for v in self.vehiculos:
            if v.cambio:
                self.origen_cambio.setdefault(v.cambio["origen"], []).append((v.s, v))

    def hay_espacio(self, seg_id, extra=0, ignorar=None):
        """¿Cabe un coche más (además de 'extra' ya comprometidos) al inicio del segmento?"""
        primero = None          # posición del último coche que entró al segmento
        for s, v in self.ocupacion.get(seg_id, []):
            if v is not ignorar and (primero is None or s < primero):
                primero = s
        necesario = (LARGO + S0) * (extra + 1)
        if primero is None:
            return self.red.carriles[seg_id].longitud + ALCANCE > necesario
        return primero - LARGO / 2 >= necesario

    def vehiculos_en_glorieta(self):
        total = 0
        for seg_id in self.red.segmentos_glorieta():
            total += len(self.ocupacion.get(seg_id, []))
        return total

    def mensaje(self, de, para, tipo, detalle):
        self.contadores[tipo] += 1
        if len(self.registro_mensajes) < 400:
            self.registro_mensajes.append({"t": round(self.tiempo, 1), "de": de, "para": para,
                                           "tipo": tipo, "detalle": detalle})

    def _detectar_colisiones(self):
        """Choque = las huellas rectangulares de dos coches se enciman."""
        actuales = set()
        lista = list(self.vehiculos)
        for i, a in enumerate(lista):
            for b in lista[i + 1:]:
                dx = a.posicion[0] - b.posicion[0]
                dz = a.posicion[1] - b.posicion[1]
                # Dos rectángulos solo pueden tocarse si sus centros están a menos
                # de una diagonal completa (la suma de sus dos semidiagonales)
                if dx * dx + dz * dz > DIAGONAL * DIAGONAL:
                    continue
                if _rectangulos_chocan(a, b):
                    actuales.add((a.id, b.id))
        self.contadores["colisiones"] += len(actuales - self._pares_en_choque)
        self._pares_en_choque = actuales

    def step(self):
        self.tiempo += DT
        self.semaforos.actualizar()        # 1. los semáforos avanzan su ciclo
        self.vehiculos.percibir()          # 2. los vehículos solicitan paso
        self.intersecciones.resolver()     # 3. las intersecciones conceden o rechazan
        self.vehiculos.decidir()           # 4. cada vehículo decide su aceleración
        self.vehiculos.mover()             # 5. todos se mueven al mismo tiempo
        self._actualizar_ocupacion()
        self.intersecciones.medir()        # 6. se mide la demanda para el siguiente paso
        self._detectar_colisiones()

    def update(self):
        filas = [i.demanda[a]["detenidos"] for i, a in self.accesos_controlados]
        vel = sum(v.velocidad for v in self.vehiculos) / max(1, len(self.vehiculos)) / M
        self.suma_velocidad += vel
        self.suma_fila += sum(filas) / len(filas)
        self.fila_maxima = max(self.fila_maxima, max(filas))
        self.muestras += 1
        if self.t % 10 == 0:               # se registra una muestra por segundo simulado
            self.record("velocidad_media", vel)
            self.record("fila_media", sum(filas) / len(filas))
            self.record("vehiculos_detenidos", sum(1 for v in self.vehiculos if v.velocidad < V_DETENIDO))

    def end(self):
        n = max(1, len(self.vehiculos))
        self.report("tiempo_espera_promedio_s", sum(v.tiempo_espera for v in self.vehiculos) / n)
        self.report("velocidad_promedio_ms", self.suma_velocidad / max(1, self.muestras))
        self.report("fila_promedio_veh", self.suma_fila / max(1, self.muestras))
        self.report("fila_maxima_veh", self.fila_maxima)
        self.report("cruces_completados", sum(i.cruces for i in self.intersecciones))
        self.report("colisiones", self.contadores["colisiones"])
        self.report("infracciones_semaforo", self.contadores["infracciones"])
        self.report("cambios_carril", self.contadores["cambios_carril"])
        self.report("espera_maxima_continua_s", max(v.espera_maxima for v in self.vehiculos))
        self.report("permisos_concedidos", self.contadores["PERMISO"])
        self.report("rechazos", self.contadores["RECHAZO"])


def _esquinas(v):
    """Cuatro esquinas de la huella rectangular de un coche (rotación 2D)."""
    c, s = math.cos(v.direccion), math.sin(v.direccion)
    x, z = v.posicion
    esquinas = []
    for px, pz in ((LARGO / 2, ANCHO / 2), (LARGO / 2, -ANCHO / 2),
                   (-LARGO / 2, -ANCHO / 2), (-LARGO / 2, ANCHO / 2)):
        esquinas.append((x + c * px - s * pz, z + s * px + c * pz))
    return esquinas


def _rectangulos_chocan(a, b):
    """Teorema de ejes separadores: dos rectángulos no se tocan si existe un
    eje (los lados de alguno de ellos) donde sus proyecciones no se enciman."""
    ea, eb = _esquinas(a), _esquinas(b)
    for v in (a, b):
        ejes = ((math.cos(v.direccion), math.sin(v.direccion)),
                (-math.sin(v.direccion), math.cos(v.direccion)))
        for ex, ez in ejes:
            pa = [px * ex + pz * ez for px, pz in ea]
            pb = [px * ex + pz * ez for px, pz in eb]
            if max(pa) < min(pb) or max(pb) < min(pa):
                return False
    return True


# Escenarios de los experimentos (los usa el notebook)
ESCENARIOS = {"ligero": 8, "moderado": 20, "elevado": 40}


def ejecutar_experimentos(escenarios=None, politicas=("fija", "adaptativa"),
                          repeticiones=3, duracion_s=300, semilla=2026):
    """Corre cada escenario con cada política. La repetición k usa la semilla
    semilla + k en ambas políticas, así parten de las mismas posiciones."""
    escenarios = escenarios or ESCENARIOS
    filas, series = [], []
    for nombre, n in escenarios.items():
        for politica in politicas:
            for k in range(repeticiones):
                params = {"n_vehiculos": n, "politica": politica, "steps": int(duracion_s / DT)}
                modelo = ModeloTrafico(params)
                resultados = modelo.run(seed=semilla + k, display=False)
                fila = {"escenario": nombre, "n_vehiculos": n, "politica": politica,
                        "repeticion": k + 1, "semilla": semilla + k}
                fila.update(resultados.reporters.iloc[0].drop(["seed"], errors="ignore").to_dict())
                filas.append(fila)
                serie = resultados.variables.ModeloTrafico.reset_index()
                serie["escenario"], serie["politica"], serie["repeticion"] = nombre, politica, k + 1
                series.append(serie)
    return pd.DataFrame(filas), pd.concat(series, ignore_index=True)
