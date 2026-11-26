"""Elementos decorativos estáticos: árboles, arbustos, jardines, bancas y farolas.
No son agentes: solo se dibujan (una vez, dentro de una lista de OpenGL)."""

from OpenGL.GL import *

from figuras import caja, cilindro, esfera

PISO = -10.0


class Arbol:
    def __init__(self, x, z, altura=70.0, pino=False, tono=0):
        self.x = x
        self.z = z
        self.altura = altura
        self.pino = pino
        # Tres tonos de verde para que no todos los árboles se vean iguales
        self.verde = [(0.20, 0.50, 0.18), (0.28, 0.58, 0.20), (0.16, 0.42, 0.22)][tono % 3]

    def draw(self):
        tronco = self.altura * 0.45
        glColor3f(0.42, 0.28, 0.16)
        cilindro(self.x, PISO, self.z, 4.5, 3.5, tronco, 8)
        glColor3f(*self.verde)
        if self.pino:
            cilindro(self.x, PISO + tronco * 0.6, self.z, 24.0, 0.0, self.altura * 0.9, 10)
        else:
            r = self.altura * 0.32
            esfera(self.x, PISO + tronco + r * 0.6, self.z, r)
            esfera(self.x + r * 0.5, PISO + tronco + r * 0.3, self.z + r * 0.3, r * 0.7)
            esfera(self.x - r * 0.4, PISO + tronco + r * 0.4, self.z - r * 0.3, r * 0.75)


class Arbusto:
    def __init__(self, x, z, radio=14.0, flores=None):
        self.x = x
        self.z = z
        self.radio = radio
        self.flores = flores      # color de flores o None

    def draw(self):
        glColor3f(0.22, 0.52, 0.20)
        esfera(self.x, PISO, self.z, self.radio, 0.8, 10)
        if self.flores:
            glColor3f(*self.flores)
            r = self.radio * 0.55
            for dx, dz in ((r, 0), (-r, r * 0.4), (0, -r), (r * 0.3, r)):
                esfera(self.x + dx, PISO + self.radio * 0.6, self.z + dz, 3.0, 1.0, 6)


class Jardin:
    """Jardinera con borde de concreto, tierra y flores de colores."""

    COLORES_FLORES = [(0.95, 0.25, 0.35), (0.98, 0.80, 0.20), (0.75, 0.40, 0.90), (1.0, 0.55, 0.20)]

    def __init__(self, x0, z0, x1, z1):
        self.x0, self.z0, self.x1, self.z1 = min(x0, x1), min(z0, z1), max(x0, x1), max(z0, z1)

    def draw(self):
        glColor3f(0.78, 0.76, 0.70)
        caja(self.x0, PISO, self.z0, self.x1, PISO + 6, self.z1)
        glColor3f(0.36, 0.25, 0.16)
        caja(self.x0 + 4, PISO, self.z0 + 4, self.x1 - 4, PISO + 7, self.z1 - 4)
        # Flores en una cuadrícula, alternando colores
        k = 0
        x = self.x0 + 12
        while x < self.x1 - 8:
            z = self.z0 + 12
            while z < self.z1 - 8:
                glColor3f(*self.COLORES_FLORES[k % len(self.COLORES_FLORES)])
                esfera(x, PISO + 10, z, 4.0, 1.0, 6)
                k += 1
                z += 16
            x += 16
            k += 1


class Banca:
    """Banca de parque. Con angulo = 0 mira hacia -z (norte); 180 mira hacia +z."""

    def __init__(self, x, z, angulo=0.0):
        self.x = x
        self.z = z
        self.angulo = angulo

    def draw(self):
        glPushMatrix()
        glTranslatef(self.x, PISO, self.z)
        glRotatef(self.angulo, 0.0, 1.0, 0.0)
        glColor3f(0.25, 0.25, 0.27)
        for px in (-14, 12):
            caja(px, 0, -6, px + 2, 9, 6)
        glColor3f(0.55, 0.36, 0.20)
        caja(-16, 9, -6, 16, 11, 6)        # asiento
        caja(-16, 11, 5, 16, 22, 7)        # respaldo
        glPopMatrix()


class Farola:
    """Poste de luz. angulo = hacia dónde apunta el brazo (grados sobre Y)."""

    def __init__(self, x, z, angulo=0.0):
        self.x = x
        self.z = z
        self.angulo = angulo

    def draw(self):
        glPushMatrix()
        glTranslatef(self.x, PISO, self.z)
        glRotatef(self.angulo, 0.0, 1.0, 0.0)
        glColor3f(0.20, 0.22, 0.25)
        cilindro(0, 0, 0, 2.5, 2.0, 105, 8)
        caja(0, 100, -1.5, 22, 104, 1.5)          # brazo hacia la calle
        glColor3f(0.30, 0.30, 0.32)
        caja(16, 96, -5, 28, 101, 5)              # pantalla
        glDisable(GL_LIGHTING)                    # el foco se ve encendido
        glColor3f(1.0, 0.95, 0.70)
        caja(17, 94, -4, 27, 96, 4)
        glEnable(GL_LIGHTING)
        glPopMatrix()
