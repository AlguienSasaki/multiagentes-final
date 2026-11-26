#Autor: Ivan Olmos Pineda
# Adaptado para el proyecto: el carro ya no se maneja con el teclado,
# ahora copia el estado de su AgenteVehiculo (AgentPy) en cada cuadro.

from OpenGL.GL import *

import numpy as np
import math

from figuras import caja

# Altura del piso en main.py
ALTURA_PISO = -10.0

ROJO_FRENO = (1.0, 0.05, 0.05)
ROJO_APAGADO = (0.45, 0.04, 0.04)
NARANJA = (1.0, 0.6, 0.0)


class Carro:

    def __init__(self, componentes, Scale, lista_carroceria):
        # Los modelos OBJ se cargan una sola vez en main.py y se comparten.
        # lista_carroceria es la lista de OpenGL de la carrocería ya pintada
        # del color de este carro.
        self.component = componentes
        self.lista_carroceria = lista_carroceria
        self.Scale = Scale
        # Se coloca el carro para que las llantas toquen el piso
        # (centro de llanta a -0.5 y radio de 0.72 en unidades del modelo)
        self.Position = np.array([0.0, ALTURA_PISO + 1.22 * Scale, 0.0])
        self.Body_Ry = 0.0
        #rotacion de llantas frontales (volante)
        self.Ll_F_Ry = 0.0
        #rotacion de las llantas sobre su eje (avance)
        self.LlantaT_angZ = 0.0
        # Traslacion base del origen a la posicon del eje trasero del carro
        self.LlantaT_pos = self.Scale * np.array([-2.3, -0.5, 0])
        # variables para llantas frontales
        self.LlantaFL_pos = self.Scale * np.array([3.5, -0.5, -1.5])
        self.LlantaFR_pos = self.Scale * np.array([3.5, -0.5, 1.5])
        # Estado que se muestra con las luces
        self.frenando = False
        self.direccional = None      # "izq", "der" o None
        self.parpadeo = False

    def sincronizar(self, agente, alpha):
        """Copia posición, orientación, llantas y luces del agente.
        alpha (0 a 1) interpola entre el paso lógico anterior y el actual para
        que el movimiento se vea suave aunque los FPS no coincidan con DT."""
        x0, z0 = agente.pos_anterior
        x1, z1 = agente.posicion
        self.Position[0] = x0 + (x1 - x0) * alpha
        self.Position[2] = z0 + (z1 - z0) * alpha
        d = math.atan2(math.sin(agente.direccion - agente.dir_anterior),
                       math.cos(agente.direccion - agente.dir_anterior))
        rumbo = agente.dir_anterior + d * alpha
        # El modelo mira hacia +X y glRotatef gira hacia -Z con angulos positivos
        self.Body_Ry = -math.degrees(rumbo)
        self.Ll_F_Ry = agente.giro_llantas
        self.LlantaT_angZ = agente.rotacion_llantas

        # Luces que muestran la máquina de estados
        self.frenando = agente.estado in ("DESACELERAR", "ESPERAR")
        self.direccional = None
        if agente.cambio:
            # El lado se obtiene proyectando el desplazamiento sobre el eje
            # derecho del carro, que en el mundo es (-sin rumbo, cos rumbo)
            ox, oz = agente.cambio["offset"]
            lado = -ox * -math.sin(rumbo) + -oz * math.cos(rumbo)
            self.direccional = "der" if lado > 0 else "izq"
        elif agente.estado == "GIRAR" and abs(agente.giro_llantas) > 8.0:
            self.direccional = "izq" if agente.giro_llantas > 0 else "der"
        self.parpadeo = int(agente.model.tiempo * 3) % 2 == 0

    # T_llanta: vector para ubicar la llanta en su posicion
    # id_llanta: para identificar si es llanta izquierda(1) o derecha(2)
    def llantaFrontal(self, T_llanta, id_llanta):
        glPushMatrix()  # Se abre rama para esta llanta frontal
        # 1. Mover al punto de anclaje delantero (izquierdo o derecho)
        glTranslatef(T_llanta[0], T_llanta[1], T_llanta[2])
        # 2. Girar sobre Y para la direccion (volante)
        glRotatef(self.Ll_F_Ry, 0.0, 1.0, 0.0)
        # 3. Girar sobre Z para simular el avance
        glRotatef(self.LlantaT_angZ, 0.0, 0.0, 1.0)
        # 4. Escalar y dibujar
        glScalef(self.Scale, self.Scale, self.Scale)
        self.component[id_llanta].render()
        glPopMatrix()

    def sombra(self):
        # Rectángulo oscuro semitransparente sobre el piso
        glDisable(GL_LIGHTING)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glDepthMask(GL_FALSE)
        glColor4f(0.0, 0.0, 0.0, 0.35)
        y = ALTURA_PISO - self.Position[1] + 0.5
        s = self.Scale
        glBegin(GL_QUADS)
        glVertex3f(-4.8 * s, y, -2.1 * s)
        glVertex3f(-4.8 * s, y, 2.1 * s)
        glVertex3f(5.3 * s, y, 2.1 * s)
        glVertex3f(5.3 * s, y, -2.1 * s)
        glEnd()
        glDepthMask(GL_TRUE)
        glDisable(GL_BLEND)
        glEnable(GL_LIGHTING)

    def luces(self):
        # Coordenadas en unidades del modelo (antes de escalar).
        # En el carro, z negativo es el lado izquierdo.
        glDisable(GL_LIGHTING)
        for lado, signo in (("izq", -1), ("der", 1)):
            # Faros delanteros
            glColor3f(1.0, 0.96, 0.75)
            caja(4.93, -0.16, signo * 1.25, 5.03, 0.12, signo * 1.70)
            # Calaveras: se encienden al frenar o esperar
            glColor3f(*(ROJO_FRENO if self.frenando else ROJO_APAGADO))
            caja(-4.70, -0.35, signo * 0.85, -4.62, -0.02, signo * 1.45)
            # Direccionales: parpadean del lado del giro o cambio de carril
            if self.direccional == lado and self.parpadeo:
                glColor3f(*NARANJA)
                caja(-4.71, -0.35, signo * 1.48, -4.60, -0.02, signo * 1.80)
                caja(4.80, -0.40, signo * 1.55, 5.00, -0.20, signo * 1.85)
        glEnable(GL_LIGHTING)

    def draw(self):
        glPushMatrix() #e0
        glTranslatef(self.Position[0], self.Position[1], self.Position[2])
        glRotatef(self.Body_Ry, 0.0, 1.0, 0.0)
        self.sombra()

        # --- RAMA 1: CARROCERIA Y LUCES ---
        glPushMatrix()
        glScalef(self.Scale, self.Scale, self.Scale)
        glCallList(self.lista_carroceria)
        self.luces()
        glPopMatrix()

        # --- RAMA 2: LLANTAS TRASERAS ---
        glPushMatrix()
        glTranslatef(self.LlantaT_pos[0], self.LlantaT_pos[1], self.LlantaT_pos[2])
        glRotatef(self.LlantaT_angZ, 0.0, 0.0, 1.0)
        glScalef(self.Scale, self.Scale, self.Scale)
        self.component[3].render()
        glPopMatrix()

        # --- RAMAS 3 y 4: LLANTAS DELANTERAS ---
        # En main.py el indice 1 es llanta_FL y el 2 es llanta_FR
        self.llantaFrontal(self.LlantaFL_pos, 1)
        self.llantaFrontal(self.LlantaFR_pos, 2)

        glPopMatrix()  # e0: Fin del carro
