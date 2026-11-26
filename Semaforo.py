from OpenGL.GL import *

from figuras import caja, cilindro, esfera

# Colores de las tres luces: (encendida, apagada)
COLORES = {
    "ROJO": ((1.0, 0.1, 0.1), (0.30, 0.05, 0.05)),
    "AMARILLO": ((1.0, 0.85, 0.0), (0.30, 0.25, 0.02)),
    "VERDE": ((0.1, 1.0, 0.2), (0.03, 0.28, 0.06)),
}


class Semaforo:
    """Poste de semáforo. Solo dibuja: el color lo decide el AgenteSemaforo."""

    def __init__(self, x, z, agente, acceso, altura=90.0):
        self.x = x
        self.z = z
        self.agente = agente      # AgenteSemaforo de modelo_multiagentes
        self.acceso = acceso      # acceso que controla este poste
        self.altura = altura

    def draw(self):
        luz = self.agente.luz(self.acceso)
        glPushMatrix()
        glTranslatef(self.x, -10.0, self.z)
        glColor3f(0.25, 0.25, 0.28)
        cilindro(0, 0, 0, 2.5, 2.5, self.altura, 10)

        # Carcasa más delgada que las luces para que se vean desde cualquier lado
        y = self.altura + 18.0
        glColor3f(0.12, 0.12, 0.12)
        caja(-4.5, y - 20, -4.5, 4.5, y + 20, 4.5)

        # Luces sin iluminación para que el color se vea brillante
        glDisable(GL_LIGHTING)
        for i, nombre in enumerate(("ROJO", "AMARILLO", "VERDE")):
            encendida, apagada = COLORES[nombre]
            glColor3f(*(encendida if luz == nombre else apagada))
            esfera(0.0, y + 12.0 - 12.0 * i, 0.0, 6.5)
        glEnable(GL_LIGHTING)
        glPopMatrix()
