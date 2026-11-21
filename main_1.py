import pygame
from pygame.locals import *

# Cargamos las bibliotecas de OpenGL
from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *

import math

# Se carga el archivo de la clase Cubo
import sys
sys.path.append('..')
from Carro import Carro

# Import obj loader
from objloader import *


#Dimension del plano, el cuadro gris
DimBoard = 2000 #300 
screen_width = 1400
screen_height = 800
#vc para el obser.
FOVY=60.0
ZNEAR=1.0
ZFAR=900.0
CENTER_X = DimBoard / 2.0
CENTER_Y = 0
CENTER_Z = DimBoard / 2.0
#Variables para definir la posicion del observador
#gluLookAt(EYE_X,EYE_Y,EYE_Z,CENTER_X,CENTER_Y,CENTER_Z,UP_X,UP_Y,UP_Z)
EYE_X = CENTER_X + 250.0  # Lo mismo de antes, pero agregandole el valor de X, en este caso ambos valores so nlo mismo, pero es importante para mantener orden y por si en un futuor no lo son
EYE_Z = CENTER_Z + 250.0 # Lo mismo que en el de las X
EYE_Y = 150.0
UP_X=0
UP_Y=1
UP_Z=0
#Variables para dibujar los ejes del sistema
X_MIN=-500
X_MAX= 500
Y_MIN=-500
Y_MAX= 500
Z_MIN=-500
Z_MAX= 500
#Dimension del plano

# Array para los objetos tipo carro
objetos = []
carros = []
ncarros = 1

#Variables para el control del observador
theta = 0.0
radius = 250
textura_piso = None

#Para aspect ratio de la imagen del piso
ANCHO_X = DimBoard
LARGO_Z = DimBoard
pygame.init()



def cargar_textura(ruta_imagen):
    superficie = pygame.image.load(ruta_imagen)
    # El tercer parámetro (1) invierte verticalmente la imagen para coincidir con el eje Y de OpenGL
    datos_imagen = pygame.image.tostring(superficie, 'RGBA', 1)
    ancho, alto = superficie.get_rect().size

    tex_id = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, tex_id)

    # Filtros para que no se pixelee demasiado al acercar o alejar la cámara
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

    # Evita que se repitan bordes extraños en las esquinas del mapa
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)

    glTexImage2D(
        GL_TEXTURE_2D,
        0,
        GL_RGBA,
        ancho,
        alto,
        0,
        GL_RGBA,
        GL_UNSIGNED_BYTE,
        datos_imagen,
    )
    return tex_id, ancho, alto

def Axis():
    glLineWidth(3.0)
    #X axis in red
    glColor3f(1.0,0.0,0.0)
    glBegin(GL_LINES)
    glVertex3f(X_MIN,0.0,0.0)
    glVertex3f(X_MAX,0.0,0.0)
    glEnd()
    #Y axis in green
    glColor3f(0.0,1.0,0.0)
    glBegin(GL_LINES)
    glVertex3f(0.0,Y_MIN,0.0)
    glVertex3f(0.0,Y_MAX,0.0)
    glEnd()
    #Z axis in blue
    glColor3f(0.0,0.0,1.0)
    glBegin(GL_LINES)
    glVertex3f(0.0,0.0,Z_MIN)
    glVertex3f(0.0,0.0,Z_MAX)
    glEnd()
    glLineWidth(1.0)


def Init():
    global textura_piso, ANCHO_X, LARGO_Z, CENTER_X, CENTER_Z

    screen = pygame.display.set_mode(
        (screen_width, screen_height), DOUBLEBUF | OPENGL)
    pygame.display.set_caption("OpenGL: cubos")

    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(FOVY, screen_width/screen_height, ZNEAR, ZFAR)

    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    #gluLookAt(EYE_X,EYE_Y,EYE_Z,CENTER_X,CENTER_Y,CENTER_Z,UP_X,UP_Y,UP_Z) # para evitar q se buguéé con un cambio brusco

    textura_piso, img_ancho, img_alto = cargar_textura('piso.png')

    # Mantener la profundidad en DimBoard (300) y expandir X según la proporción 16:9
    aspect_ratio = img_ancho / float(img_alto)
    LARGO_Z = DimBoard
    ANCHO_X = DimBoard * aspect_ratio  # Para 16:9 dará aprox. 533.33

    # Recalcular el centro para que la cámara siga orbitando exactamente en medio
    CENTER_X = ANCHO_X / 2.0
    CENTER_Z = LARGO_Z / 2.0

    lookat()
    glClearColor(0,0,0,0)
    glEnable(GL_DEPTH_TEST)
    glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
    glShadeModel(GL_SMOOTH)
        
    #glLightfv(GL_LIGHT0, GL_POSITION,  (-40, 200, 100, 0.0))
    glLightfv(GL_LIGHT0, GL_POSITION,  (0, 200, 0, 0.0))
    glLightfv(GL_LIGHT0, GL_AMBIENT, (0.5, 0.5, 0.5, 1.0))
    glLightfv(GL_LIGHT0, GL_DIFFUSE, (0.5, 0.5, 0.5, 1.0))
    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)
    glEnable(GL_COLOR_MATERIAL)
    glEnable(GL_NORMALIZE)
    # Se generan los componentes graficos del carro y se gregan
    # al array objetos
    objetos.append(OBJ("carroceria.obj", swapyz=True))
    objetos[0].generate()
    objetos.append(OBJ("llanta_FL.obj", swapyz=True))
    objetos[1].generate()
    objetos.append(OBJ("llanta_FR.obj", swapyz=True))
    objetos[2].generate()
    objetos.append(OBJ("llantas_traseras.obj", swapyz=True))
    objetos[3].generate()
    

    # se genera un carro
    for i in range(ncarros):
        carros.append(Carro(DimBoard, 1.0, 10.0))
        carros[-1].getComponents(objetos)

    #textura_piso = cargar_textura('piso.png')
#Se mueve al observador circularmente al rededor del plano XZ a una altura fija (EYE_Y)

def lookat():
  global EYE_X, EYE_Z, radius
  rad = math.radians(theta)
  EYE_X = CENTER_X + radius * math.cos(rad)
  EYE_Z = CENTER_Z + radius * math.sin(rad)
  glLoadIdentity()
  gluLookAt(EYE_X, EYE_Y, EYE_Z, CENTER_X, CENTER_Y, CENTER_Z, UP_X, UP_Y, UP_Z)

def display():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    Axis()

    # --- DIBUJAR PISO CON TEXTURA PNG ---
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, textura_piso)

    # Blanco puro para que la textura conserve sus colores originales bajo la luz
    glColor3f(1.0, 1.0, 1.0)

    # Altura Y donde tocan las llantas (usa -10.0 o el valor exacto que ajustaste)
    altura_piso = -10.0

    glBegin(GL_QUADS)
    # Normal apuntando hacia +Y para reaccionar correctamente a GL_LIGHT0
    glNormal3f(0.0, 1.0, 0.0)

    # Vértice 1: Esquina origen (0, 0) -> UV (0, 0)
    glTexCoord2f(0.0, 0.0)
    glVertex3d(0.0, altura_piso, 0.0)

    # Vértice 2: Esquina +Z (0, DimBoard) -> UV (0, 1)
    glTexCoord2f(0.0, 1.0)
    glVertex3d(0.0, altura_piso, DimBoard)

    # Vértice 3: Esquina opuesta (DimBoard, DimBoard) -> UV (1, 1)
    glTexCoord2f(1.0, 1.0)
    glVertex3d(DimBoard, altura_piso, DimBoard)

    # Vértice 4: Esquina +X (DimBoard, 0) -> UV (1, 0)
    glTexCoord2f(1.0, 0.0)
    glVertex3d(DimBoard, altura_piso, 0.0)
    glEnd()

    # Apagar las texturas 2D después de dibujar el piso para no afectar otros objetos sin textura
    glBindTexture(GL_TEXTURE_2D, 0)
    glDisable(GL_TEXTURE_2D)


    # Se dibuja el carro
    # No dibujo nadota por ahora :P
    for car in carros:
        car.update()
        car.draw()
    
done = False
Init()
while not done:
    keys = pygame.key.get_pressed()
    #avanzar observador
    if keys[pygame.K_LEFT]:
        theta = (theta + 0.7) % 360
        lookat()        
    if keys[pygame.K_RIGHT]:
        theta = (theta - 0.7) % 360
        lookat()        
    # solo se controla el ultimo carrito en el array
    if keys[pygame.K_w]:
        carros[-1].setAvanza()
    if keys[pygame.K_a]:
        carros[-1].setRota('L')
    if keys[pygame.K_d]:
        carros[-1].setRota('R')
    
    for event in pygame.event.get():
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                done = True

    display()

    pygame.display.flip()
    pygame.time.wait(5)

pygame.quit()
