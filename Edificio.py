from OpenGL.GL import *

class Edificio:
    def __init__(self, x, y, z, scale, modelo, ancho_base=18.0, largo_base=38.0):
        self.x = x
        self.y = y
        self.z = z
        self.scale = scale  # tupla (esc_x, esc_y, esc_z)
        self.modelo = modelo

        medio_ancho = (ancho_base * scale[0]) / 2.0
        medio_largo = (largo_base * scale[2]) / 2.0

        self.min_x = x - medio_ancho
        self.max_x = x + medio_ancho
        self.min_z = z - medio_largo
        self.max_z = z + medio_largo

    def colisiona_con(self, x, z, radio):
        return (
            x + radio > self.min_x and
            x - radio < self.max_x and
            z + radio > self.min_z and
            z - radio < self.max_z
        )

    def draw(self):
        glPushMatrix()
        glTranslatef(self.x, self.y, self.z)
        glScalef(*self.scale)
        self.modelo.render()
        glPopMatrix()
