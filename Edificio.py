import math
from OpenGL.GL import *

from figuras import caja, cilindro

ALTURA_PISO = -10.0
ALTO_PLANTA = 46.0       # altura de cada piso (≈ 3 m)
ALTO_PLANTA_BAJA = 50.0


class Edificio:
    """Edificio con el modelo OBJ original (models/edificio.obj)."""

    def __init__(self, x, y, z, scale, modelo, angulo=0.0):
        self.x = x
        self.y = y
        self.z = z
        self.scale = scale  # tupla (esc_x, esc_y, esc_z)
        self.modelo = modelo
        self.angulo = angulo

    def draw(self):
        glPushMatrix()
        glTranslatef(self.x, self.y, self.z)
        glRotatef(self.angulo, 0.0, 1.0, 0.0)
        glScalef(*self.scale)
        glColor3f(1.0, 1.0, 1.0)   # la textura palette.png se multiplica por este color
        self.modelo.render()
        glPopMatrix()


class EdificioUrbano:
    """Edificio hecho con cajas: fachada con ventanas por piso, planta baja
    con puerta y aparadores, y azotea con pretil, tinaco y aire acondicionado.

    (x0, z0)-(x1, z1) es la huella en el piso y 'puerta' indica la fachada
    que da a la calle: 'N' (z menor), 'S' (z mayor), 'E' (x mayor) u 'O'.
    """

    def __init__(self, x0, z0, x1, z1, pisos, color, puerta="S", tinaco=True):
        self.x0, self.z0 = min(x0, x1), min(z0, z1)
        self.x1, self.z1 = max(x0, x1), max(z0, z1)
        self.pisos = pisos
        self.color = color
        self.puerta = puerta
        self.tinaco = tinaco
        self.altura = ALTO_PLANTA_BAJA + pisos * ALTO_PLANTA

    def _fachadas(self):
        """Cada fachada: esquina inicial, esquina final y normal hacia afuera."""
        x0, z0, x1, z1 = self.x0, self.z0, self.x1, self.z1
        return {
            "S": ((x0, z1), (x1, z1), (0.0, 1.0)),
            "N": ((x1, z0), (x0, z0), (0.0, -1.0)),
            "E": ((x1, z1), (x1, z0), (1.0, 0.0)),
            "O": ((x0, z0), (x0, z1), (-1.0, 0.0)),
        }

    def _rectangulo(self, p0, p1, normal, u0, u1, y0, y1, separacion=1.0):
        """Rectángulo pegado a una fachada, de u0 a u1 (distancia a lo largo de
        la fachada) y de y0 a y1. Se separa un poco para que no parpadee."""
        largo = math.dist(p0, p1)
        dx, dz = (p1[0] - p0[0]) / largo, (p1[1] - p0[1]) / largo
        ox, oz = normal[0] * separacion, normal[1] * separacion
        glNormal3f(normal[0], 0.0, normal[1])
        for u, y in ((u0, y0), (u1, y0), (u1, y1), (u0, y1)):
            glVertex3f(p0[0] + dx * u + ox, y, p0[1] + dz * u + oz)

    def _dibujar_fachada(self, nombre, p0, p1, normal):
        largo = math.dist(p0, p1)
        piso = ALTURA_PISO
        columnas = max(1, int(largo // 42))
        paso = largo / columnas
        glBegin(GL_QUADS)
        # Ventanas de los pisos superiores; algunas se ven iluminadas
        for f in range(self.pisos):
            y = piso + ALTO_PLANTA_BAJA + f * ALTO_PLANTA + 12.0
            for c in range(columnas):
                if (f * 7 + c * 3 + len(nombre)) % 9 == 0:
                    glColor3f(0.95, 0.85, 0.55)
                else:
                    glColor3f(0.32, 0.45, 0.58)
                u = c * paso + paso / 2
                self._rectangulo(p0, p1, normal, u - 12.0, u + 12.0, y, y + 24.0)
        # Planta baja: aparadores y, en la fachada principal, la puerta
        glColor3f(0.25, 0.33, 0.40)
        self._rectangulo(p0, p1, normal, 8.0, largo - 8.0, piso + 8.0, piso + 36.0, 3.0)
        if nombre == self.puerta:
            glColor3f(0.35, 0.22, 0.12)
            self._rectangulo(p0, p1, normal, largo / 2 - 14.0, largo / 2 + 14.0, piso, piso + 40.0, 4.0)
        glEnd()

    def draw(self):
        x0, z0, x1, z1 = self.x0, self.z0, self.x1, self.z1
        piso = ALTURA_PISO
        techo = piso + self.altura
        r, g, b = self.color

        # Cuerpo y franja más oscura de la planta baja
        glColor3f(r, g, b)
        caja(x0, piso, z0, x1, techo, z1)
        glColor3f(r * 0.7, g * 0.7, b * 0.7)
        caja(x0 - 2, piso, z0 - 2, x1 + 2, piso + ALTO_PLANTA_BAJA - 4, z1 + 2)
        # Cornisas entre pisos
        glColor3f(min(1, r * 1.15), min(1, g * 1.15), min(1, b * 1.15))
        for f in range(1, self.pisos + 1):
            y = piso + ALTO_PLANTA_BAJA + f * ALTO_PLANTA - 4.0
            caja(x0 - 1.5, y, z0 - 1.5, x1 + 1.5, y + 3.0, z1 + 1.5)

        for nombre, (p0, p1, normal) in self._fachadas().items():
            self._dibujar_fachada(nombre, p0, p1, normal)

        # Azotea: pretil, cuarto de máquinas, aire acondicionado y tinaco
        glColor3f(0.55, 0.55, 0.55)
        borde = 6.0
        caja(x0, techo, z0, x1, techo + 10, z0 + borde)
        caja(x0, techo, z1 - borde, x1, techo + 10, z1)
        caja(x0, techo, z0, x0 + borde, techo + 10, z1)
        caja(x1 - borde, techo, z0, x1, techo + 10, z1)
        cx, cz = (x0 + x1) / 2, (z0 + z1) / 2
        glColor3f(0.75, 0.75, 0.72)
        caja(cx - 30, techo, cz - 25, cx + 10, techo + 28, cz + 15)
        glColor3f(0.85, 0.87, 0.9)
        caja(x0 + 18, techo, z0 + 18, x0 + 38, techo + 14, z0 + 34)
        caja(x0 + 46, techo, z0 + 18, x0 + 66, techo + 14, z0 + 34)
        if self.tinaco:
            glColor3f(0.15, 0.15, 0.17)
            cilindro(x1 - 35, techo, z1 - 35, 14, 14, 26)
