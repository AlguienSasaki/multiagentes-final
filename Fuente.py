from OpenGL.GL import *
from OpenGL.GLU import *

from figuras import quadric, cilindro

# Espejos de agua del modelo: (altura sobre la base, radio) en unidades del mundo
NIVELES_AGUA = [(26.0, 66.0), (72.0, 24.0), (98.0, 31.0)]


class Fuente:
    def __init__(self, obj_model, pos, scale=(1.0, 1.0, 1.0)):
        self.model = obj_model
        self.Position = [float(pos[0]), float(pos[1]), float(pos[2])]
        self.scale = scale

    def draw(self, tiempo=0.0):
        glPushMatrix()
        glTranslatef(self.Position[0], self.Position[1], self.Position[2])

        # Pasto de la isleta de la glorieta y modelo original de la fuente
        glColor3f(0.40, 0.62, 0.30)
        cilindro(0, 0, 0, 88.0, 88.0, 1.5, 32)
        glPushMatrix()
        glScalef(self.scale[0], self.scale[1], self.scale[2])
        # El modelo no está centrado en su origen ni apoyado en y = 0
        glTranslatef(-0.355, -0.0095, -0.501)
        self.model.render()
        glPopMatrix()

        # Agua semitransparente: discos horizontales y un chorro al centro
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glDepthMask(GL_FALSE)
        glColor4f(0.35, 0.65, 0.95, 0.75)
        for altura, radio in NIVELES_AGUA:
            glPushMatrix()
            glTranslatef(0.0, altura, 0.0)
            glRotatef(-90.0, 1.0, 0.0, 0.0)
            gluDisk(quadric(), 0.0, radio, 24, 1)
            glPopMatrix()
        # El chorro sube y baja un poco con el tiempo de la simulación
        alto = 30.0 + 6.0 * abs((tiempo % 2.0) - 1.0)
        glColor4f(0.70, 0.85, 1.0, 0.55)
        cilindro(0, 98.0, 0, 4.0, 1.5, alto, 10)
        glDepthMask(GL_TRUE)
        glDisable(GL_BLEND)
        glPopMatrix()
