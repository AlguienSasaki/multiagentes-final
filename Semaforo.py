import math
import time
from OpenGL.GL import *


class Semaforo:
    """Representa un semaforo 3D de dos partes:
    1) Poste gris + encapsulado amarillo (pieza fija).
    2) Barra interior que cambia de color segun el estado (VERDE, AMARILLO, ROJO).
    """

    ESTADOS = ("VERDE", "AMARILLO", "ROJO")

    MATERIAL_POR_ESTADO = {
        "VERDE": "luz_verde",
        "AMARILLO": "luz_amarilla",
        "ROJO": "luz_roja",
        "APAGADO": "luz_apagada",
    }

    COLORES_DEFECTO = {
        "VERDE": (0.10, 0.86, 0.28),
        "AMARILLO": (1.00, 0.82, 0.08),
        "ROJO": (0.96, 0.14, 0.14),
        "APAGADO": (0.18, 0.18, 0.18),
    }

    EMISION_DEFECTO = {
        "VERDE": (0.04, 0.30, 0.08),
        "AMARILLO": (0.32, 0.24, 0.02),
        "ROJO": (0.32, 0.03, 0.03),
        "APAGADO": (0.0, 0.0, 0.0),
    }

    def __init__(
        self,
        modelo_poste,
        modelo_barra,
        pos=(0.0, -10.0, 0.0),
        scale=(10.0, 10.0, 10.0),
        rot_y=0.0,
        estado_inicial="ROJO",
        duraciones=None,
        auto_ciclo=True,
    ):
        self.modelo_poste = modelo_poste
        self.modelo_barra = modelo_barra
        self.Position = [float(pos[0]), float(pos[1]), float(pos[2])]

        if isinstance(scale, (int, float)):
            self.scale = (float(scale), float(scale), float(scale))
        else:
            self.scale = (float(scale[0]), float(scale[1]), float(scale[2]))

        self.rot_y = float(rot_y)
        self.auto_ciclo = bool(auto_ciclo)

        self.duraciones = {
            "VERDE": 4.0,
            "AMARILLO": 1.5,
            "ROJO": 4.0,
        }
        if duraciones:
            for k, v in duraciones.items():
                self.duraciones[k.upper()] = float(v)

        estado_norm = estado_inicial.upper()
        if estado_norm not in self.MATERIAL_POR_ESTADO:
            raise ValueError(f"Estado invalido para Semaforo: {estado_inicial}")
        self.estado = estado_norm

        self._tiempo_en_estado = 0.0
        self._ultimo_tiempo = time.monotonic()

        # Compilamos la geometria de la barra sin fijar glColor dentro del Display List
        # para poder cambiar el color dinamicamente segun el estado.
        self._barra_gl_list = self._obtener_o_compilar_barra(modelo_barra)

    @staticmethod
    def _obtener_o_compilar_barra(modelo_barra):
        gl_list = getattr(modelo_barra, "_gl_list_dinamico", 0)
        if gl_list:
            return gl_list

        gl_list = glGenLists(1)
        glNewList(gl_list, GL_COMPILE)
        glFrontFace(GL_CCW)
        for vertices, normals, texture_coords, _material in modelo_barra.faces:
            glBegin(GL_POLYGON)
            for i in range(len(vertices)):
                if normals[i] > 0:
                    glNormal3fv(modelo_barra.normals[normals[i] - 1])
                if texture_coords[i] > 0:
                    glTexCoord2fv(modelo_barra.texcoords[texture_coords[i] - 1])
                glVertex3fv(modelo_barra.vertices[vertices[i] - 1])
            glEnd()
        glEndList()

        modelo_barra._gl_list_dinamico = gl_list
        return gl_list

    def _obtener_color_estado(self):
        mat_name = self.MATERIAL_POR_ESTADO[self.estado]
        mtl = getattr(self.modelo_barra, "mtl", None)
        if mtl and mat_name in mtl and "Kd" in mtl[mat_name]:
            kd = mtl[mat_name]["Kd"]
            return (kd[0], kd[1], kd[2])
        return self.COLORES_DEFECTO[self.estado]

    def _obtener_emision_estado(self):
        mat_name = self.MATERIAL_POR_ESTADO[self.estado]
        mtl = getattr(self.modelo_barra, "mtl", None)
        if mtl and mat_name in mtl and "Ke" in mtl[mat_name]:
            ke = mtl[mat_name]["Ke"]
            return (ke[0], ke[1], ke[2])
        return self.EMISION_DEFECTO[self.estado]

    def set_estado(self, nuevo_estado):
        estado_norm = nuevo_estado.upper()
        if estado_norm not in self.MATERIAL_POR_ESTADO:
            raise ValueError(f"Estado invalido: {nuevo_estado}")
        self.estado = estado_norm
        self._tiempo_en_estado = 0.0
        self._ultimo_tiempo = time.monotonic()

    def siguiente_estado(self):
        if self.estado in self.ESTADOS:
            idx = self.ESTADOS.index(self.estado)
            self.set_estado(self.ESTADOS[(idx + 1) % len(self.ESTADOS)])
        else:
            self.set_estado(self.ESTADOS[0])
        return self.estado

    def set_auto_ciclo(self, activo):
        self.auto_ciclo = bool(activo)
        self._ultimo_tiempo = time.monotonic()

    def toggle_auto_ciclo(self):
        self.set_auto_ciclo(not self.auto_ciclo)
        return self.auto_ciclo

    def tiempo_restante(self):
        if self.estado not in self.duraciones:
            return 0.0
        return max(0.0, self.duraciones[self.estado] - self._tiempo_en_estado)

    def esta_en_rojo(self):
        return self.estado == "ROJO"

    def esta_en_amarillo(self):
        return self.estado == "AMARILLO"

    def esta_en_verde(self):
        return self.estado == "VERDE"

    def puede_pasar(self, permitir_amarillo=False):
        if permitir_amarillo:
            return self.estado in ("VERDE", "AMARILLO")
        return self.estado == "VERDE"

    def update(self, dt=None):
        ahora = time.monotonic()
        if dt is None:
            dt = ahora - self._ultimo_tiempo
        self._ultimo_tiempo = ahora

        if not self.auto_ciclo or self.estado not in self.duraciones:
            return False

        self._tiempo_en_estado += max(0.0, float(dt))
        duracion = self.duraciones[self.estado]
        if self._tiempo_en_estado >= duracion:
            self.siguiente_estado()
            return True
        return False

    def colisiona_con(self, x, z, radio):
        """Comprueba colision solo contra los dos postes laterales,
        permitiendo que el carro pase libremente por debajo del arco.
        """
        dx = x - self.Position[0]
        dz = z - self.Position[2]

        # Transformar al sistema local del semaforo (rotacion inversa -rot_y)
        rad = math.radians(self.rot_y)
        cos_r = math.cos(rad)
        sin_r = math.sin(rad)
        local_x = dx * cos_r - dz * sin_r
        local_z = dx * sin_r + dz * cos_r

        sx, _, sz = self.scale
        z_half = 0.7 * sz

        # Postes en X local: [-7.0, -5.6] y [5.6, 7.0]
        postes_x = (
            (-7.0 * sx, -5.6 * sx),
            (5.6 * sx, 7.0 * sx),
        )
        for min_x, max_x in postes_x:
            if (
                local_x + radio > min_x
                and local_x - radio < max_x
                and local_z + radio > -z_half
                and local_z - radio < z_half
            ):
                return True
        return False

    def draw(self):
        glPushMatrix()
        glTranslatef(self.Position[0], self.Position[1], self.Position[2])
        glRotatef(self.rot_y, 0.0, 1.0, 0.0)
        glScalef(self.scale[0], self.scale[1], self.scale[2])

        # Limpiar cualquier textura activa antes de dibujar materiales de color solido
        glBindTexture(GL_TEXTURE_2D, 0)
        glDisable(GL_TEXTURE_2D)

        # Parte 1: Poste gris y encapsulado amarillo (fijos)
        self.modelo_poste.render()

        # Parte 2: Barra de estado con color dinamico
        r, g, b = self._obtener_color_estado()
        er, eg, eb = self._obtener_emision_estado()
        glColor3f(r, g, b)
        glMaterialfv(GL_FRONT_AND_BACK, GL_EMISSION, (er, eg, eb, 1.0))
        glCallList(self._barra_gl_list)

        # Restaurar estado OpenGL para no afectar otros objetos
        glMaterialfv(GL_FRONT_AND_BACK, GL_EMISSION, (0.0, 0.0, 0.0, 1.0))
        glColor3f(1.0, 1.0, 1.0)
        glPopMatrix()
