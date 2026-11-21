#Autor: Ivan Olmos Pineda

import pygame
from pygame.locals import *

# Cargamos las bibliotecas de OpenGL
from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *

# Import obj loader
from objloader import *

import numpy as np
import random
import math

class Carro:
    
    def __init__(self, dim, vel, Scale):
        self.DimBoard = dim
        #Se inicializa una posicion en el tablero
        #self.Position = np.array([0.0, 0.0, 0.0]) # inincializacion en el eje 0,0,0
        self.Position = np.array([dim/2.0, 0.0, dim/2.0])
        #Se inicializa un vector de direccion
        self.Direction = np.array([1.0, 0.0, 0.0])
        #Se normaliza el vector de direccion
        m = math.sqrt(self.Direction[0]*self.Direction[0] + self.Direction[2]*self.Direction[2])
        self.Direction[0] /= m
        self.Direction[2] /= m
        #Se almacena la magnitud de velocidad
        self.vel = vel
        #arreglo de cubos
        self.component = []
        #Variables de control globales del carro
        self.Avanza = False
        self.Rota = False
        self.Scale = Scale
        self.Body_Ry = 0.0
        #rotacion de llantas frontales
        self.Ll_F_Ry = 0.0
        
        self.cos_ang = 0.0
        self.sin_ang = 0.0
        self.cos_angF = 0.0
        self.sin_angF = 0.0
        #Matrices para optimizacion de operadores
        # La siguiente declaracion asume que en tiempo de ejecucion se transpone la matriz
        # para usarla como la requiere OpenGL
        # self.M_Carroceria = np.identity(4, dtype=np.float32)
        # Para optimizar, se declaran las matrices identidad traspuestas
        self.M_Carroceria = np.identity(4, dtype=np.float32).T
        # Matriz para las llantas traseras
        self.M_Llantas_traseras = np.identity(4, dtype=np.float32).T
        # Matriz para la llanta frontal izquierda
        self.M_Llanta_F = np.identity(4, dtype=np.float32).T
        # Matriz para la llanta frontal derecha
        #self.M_Llanta_FR = np.identity(4, dtype=np.float32).T

        # Se define el radio base del objeto llanta (depende del tamaño del objeto grafico)
        # (se debe modificar manualmente dependiendo de dicho tamaño)
        self.Llanta_radio_base = 1.0
        # Radio de la llanta considerando la escala del carro
        self.Llanta_radio = self.Llanta_radio_base * self.Scale
        # Traslacion base del origen a la posicon del eje trasero del carro
        # Este vector depende de la escala del carro
        self.LlantaT_dist = self.Scale * np.array([-2.3,-0.5,0])
        self.LlantaT_pos = np.copy(self.LlantaT_dist)
        # Para que las llantas tengan el efecto de girar hacia adelante
        # se debe calcular el angulo de rotacion de las mismas a partir de la formula
        # theta = (360 * d) / (2*pi*r), donde d es la distancia a recorrer y r el 
        # radio de la llanta
        # La distancia a recorrer depende de la velocidad (el vector de direccion es unitario)
        # como se desea que el carrito avance, la rotación es en contra de las manecillas del reloj
        # con respecto al eje Z, por lo tanto es una rotación negativa
        self.LlantaT_angZ_delta = math.radians((-1.0 * 360.0 * self.vel) / (2.0 * np.pi * self.Llanta_radio))
        # angulo de rotacion inicial para las llantas frontales y traseras
        self.LlantaT_angZ = 0.0
        # variables para llantas frontales
        self.LlantaFL_pos = self.Scale * np.array([3.5, -0.5, -1.5])
        self.LlantaFR_pos = self.Scale * np.array([3.5, -0.5, 1.5])
        # Distancia entre ejes
        self.L = abs(self.LlantaFL_pos[0] - self.LlantaT_pos[0])
        # Intervalo de tiempo por frame
        self.dt = 100

    def getComponents(self, comp):
        self.component = comp
        
    def setAvanza(self):
        self.Avanza = True
#        
    def setRota(self, dir):
         # Limite de giro para que las llantas no atraviesen la carroceria
         max_giro = 35.0
         paso_giro = 2.0
         if dir == 'L':
           self.Ll_F_Ry = min(self.Ll_F_Ry + paso_giro, max_giro)
         elif dir == 'R':
           self.Ll_F_Ry = max(self.Ll_F_Ry - paso_giro, -max_giro)


        
    def update(self):
        if self.Avanza:
            if abs(self.Ll_F_Ry) > 0.1:
                vel_angular = (self.vel / self.L) * math.tan(
                    math.radians(self.Ll_F_Ry)
                )
                self.Body_Ry += math.degrees(vel_angular)

                # Actualizar vector de direccion segun la rotacion actual del cuerpo
                rad_body = math.radians(self.Body_Ry)
                self.Direction[0] = math.cos(rad_body)
                self.Direction[2] = -math.sin(rad_body)

                # Mover el carro en el plano XZ
                self.Position[0] += self.Direction[0] * self.vel
                self.Position[2] += self.Direction[2] * self.vel

                # Rotar las llantas sobre su eje de rodamiento (Z)
                self.LlantaT_angZ += math.degrees(self.LlantaT_angZ_delta)

                # Reiniciar bandera para que requiera mantener presionada la tecla W
                self.Avanza = False

    # T_llanta: vector para ubicar la llanta en su posicion
    # id_llanta: para identificar si es llanta izquierda(1) o derecha(2)
    def llantaFrontal(self, T_llanta, id_llanta):
        glPushMatrix()  # Se abre rama para esta llanta frontal
      # 1. Mover al punto de anclaje delantero (izquierdo o derecho)
        glTranslatef(T_llanta[0], T_llanta[1], T_llanta[2])
        # 2. Girar sobre Y para la direccion (volante)
        glRotatef(self.Ll_F_Ry, 0.0, 1.0, 0.0)
        # 3. Girar sobre Z para simular q
        glRotatef(self.LlantaT_angZ, 0.0, 0.0, 1.0)
        # 4. Escalar y dibujar
        glScalef(self.Scale, self.Scale, self.Scale)
        self.component[id_llanta].render()
        glPopMatrix()  # Se
    
    def draw(self):
        if not self.component:
            return

        glPushMatrix() #e0
        # Se define la maquina de estados
        # Se actualizan los componentes de la matriz optimizada
        glTranslatef(self.Position[0], self.Position[1], self.Position[2])
        glRotatef(self.Body_Ry, 0.0, 1.0, 0.0)

        # --- RAMA 1: CARROCERIA ---
        glPushMatrix()
        glScalef(self.Scale, self.Scale, self.Scale)
        self.component[0].render()
        glPopMatrix()

        # --- RAMA 2: LLANTAS TRASERAS ---
        glPushMatrix()
        glTranslatef(
            self.LlantaT_pos[0], self.LlantaT_pos[1], self.LlantaT_pos[2]
        )
        glRotatef(self.LlantaT_angZ, 0.0, 0.0, 1.0)
        glScalef(self.Scale, self.Scale, self.Scale)
        self.component[3].render()
        glPopMatrix()

        # --- RAMAS 3 y 4: LLANTAS DELANTERAS ---
        # En main.py el indice 1 es llanta_FL y el 2 es llanta_FR
        self.llantaFrontal(self.LlantaFL_pos, 1)
        self.llantaFrontal(self.LlantaFR_pos, 2)

        glPopMatrix()  # e0: Fin del carro
        
        

                
