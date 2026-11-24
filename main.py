import pygame
from pygame.locals import *

# Cargamos las bibliotecas de OpenGL
from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *

import math

# Se carga el archivo de la clase Cubo
import sys

sys.path.append("..")
from Carro import Carro
from Edificio import Edificio
from Fuente import Fuente

# Import obj loader
from objloader import *


# Dimension del plano, el cuadro gris
DimBoard = 1800  # 300
screen_width = 1050
screen_height = 600
# vc para el obser.
FOVY = 60.0
ZNEAR = 1
ZFAR = 6800
CENTER_X = DimBoard / 2.0
CENTER_Y = 0
CENTER_Z = DimBoard / 2.0
# Variables para definir la posicion del observador
# gluLookAt(EYE_X,EYE_Y,EYE_Z,CENTER_X,CENTER_Y,CENTER_Z,UP_X,UP_Y,UP_Z)
EYE_X = (
    CENTER_X + 250.0
)  # Lo mismo de antes, pero agregandole el valor de X, en este caso ambos valores so nlo mismo, pero es importante para mantener orden y por si en un futuor no lo son
EYE_Z = CENTER_Z + 250.0  # Lo mismo que en el de las X
EYE_Y = 150.0
UP_X = 0
UP_Y = 1
UP_Z = 0
# Variables para dibujar los ejes del sistema
X_MIN = -500
X_MAX = 500
Y_MIN = -500
Y_MAX = 500
Z_MIN = -500
Z_MAX = 500
# Dimension del plano

# Array para los objetos tipo carro
objetos = []
carros = []
edificios = []
fuente = []
ncarros = 1
modelo_edificio = None

# Variables para el control del observador
theta = 0.0
radius = 250
textura_piso = None

# Para aspect ratio de la imagen del piso
ANCHO_X = DimBoard
LARGO_Z = DimBoard
pygame.init()


def cargar_textura(ruta_imagen):
    superficie = pygame.image.load(ruta_imagen)
    # El tercer parámetro (1) invierte verticalmente la imagen para coincidir con el eje Y de OpenGL
    datos_imagen = pygame.image.tostring(superficie, "RGBA", 1)
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
    # X axis in red
    glColor3f(1.0, 0.0, 0.0)
    glBegin(GL_LINES)
    glVertex3f(X_MIN, 0.0, 0.0)
    glVertex3f(X_MAX, 0.0, 0.0)
    glEnd()
    # Y axis in green
    glColor3f(0.0, 1.0, 0.0)
    glBegin(GL_LINES)
    glVertex3f(0.0, Y_MIN, 0.0)
    glVertex3f(0.0, Y_MAX, 0.0)
    glEnd()
    # Z axis in blue
    glColor3f(0.0, 0.0, 1.0)
    glBegin(GL_LINES)
    glVertex3f(0.0, 0.0, Z_MIN)
    glVertex3f(0.0, 0.0, Z_MAX)
    glEnd()
    glLineWidth(1.0)

def dibujar_piso():
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, textura_piso)

    glColor3f(1.0, 1.0, 1.0)
    altura_piso = -10.0

    glBegin(GL_QUADS)
    glNormal3f(0.0, 1.0, 0.0)

    glTexCoord2f(0.0, 0.0)
    glVertex3d(0.0, altura_piso, 0.0)

    glTexCoord2f(0.0, 1.0)
    glVertex3d(0.0, altura_piso, LARGO_Z)

    glTexCoord2f(1.0, 1.0)
    glVertex3d(ANCHO_X, altura_piso, LARGO_Z)

    glTexCoord2f(1.0, 0.0)
    glVertex3d(ANCHO_X, altura_piso, 0.0)
    glEnd()

    glBindTexture(GL_TEXTURE_2D, 0)
    glDisable(GL_TEXTURE_2D)


def Init():
    global textura_piso, ANCHO_X, LARGO_Z, CENTER_X, CENTER_Z, modelo_edificio, edificios, modelo_fuente, fuente

    # 1. PRIMERO crear la ventana y el contexto OpenGL
    screen = pygame.display.set_mode((screen_width, screen_height), DOUBLEBUF | OPENGL)
    pygame.display.set_caption("OpenGL: cubos")

    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(FOVY, screen_width / screen_height, ZNEAR, ZFAR)

    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()

    # 2. SEGUNDO cargar la textura y calcular las dimensiones reales del mapa
    textura_piso, img_ancho, img_alto = cargar_textura("piso.png")

    aspect_ratio = img_ancho / float(img_alto)
    LARGO_Z = DimBoard
    ANCHO_X = DimBoard * aspect_ratio

    CENTER_X = ANCHO_X / 2.0
    CENTER_Z = LARGO_Z / 2.0

    lookat()
    glClearColor(0, 0, 0, 0)
    glEnable(GL_DEPTH_TEST)
    glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
    glShadeModel(GL_SMOOTH)

    glLightfv(GL_LIGHT0, GL_POSITION, (0, 200, 0, 0.0))
    glLightfv(GL_LIGHT0, GL_AMBIENT, (0.5, 0.5, 0.5, 1.0))
    glLightfv(GL_LIGHT0, GL_DIFFUSE, (0.5, 0.5, 0.5, 1.0))
    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)
    glEnable(GL_COLOR_MATERIAL)
    glEnable(GL_NORMALIZE)

    # 3. TERCERO cargar los modelos .obj (ya con contexto OpenGL y dimensiones listas)
    modelo_edificio = OBJ("models/edificio.obj", swapyz=False)
    modelo_edificio.generate()

    modelo_fuente= OBJ("models/fuente.obj", swapyz=False)
    modelo_fuente.generate()

    esc_x, esc_y, esc_z = 55.0, 14.0, 14.0
    medio_ancho = (18.0 * esc_x) / 2.0
    medio_largo = (38.0 * esc_z) / 2.0

    escala_ed = (55.0, 14.0, 14.0)
    posiciones_edificios = [
        (ANCHO_X * 0.25 - 60, LARGO_Z * 0.25 + 45),
        (ANCHO_X * 0.75 + 60, LARGO_Z * 0.25 + 45),
        (ANCHO_X * 0.25 - 60, LARGO_Z * 0.75 - 45),
        (ANCHO_X * 0.75 + 60, LARGO_Z * 0.75 - 45),
    ]


    posicion_fuente= [
        (ANCHO_X * 0.5 , LARGO_Z * 0.5 ),
    ]

    edificios.clear()
    fuente.clear()
    for cx, cz in posiciones_edificios:
        edificios.append(Edificio(cx, -10.0, cz, escala_ed, modelo_edificio))
    
    escala_fuente = (800.0, 800.0, 800.0)
    for cx, cz in posicion_fuente:
        fuente.append(Fuente(modelo_fuente, (cx, 0.0, cz), scale=escala_fuente))

    objetos.append(OBJ("models/carroceria.obj", swapyz=True))
    objetos[0].generate()
    objetos.append(OBJ("models/llanta_FL.obj", swapyz=True))
    objetos[1].generate()
    objetos.append(OBJ("models/llanta_FR.obj", swapyz=True))
    objetos[2].generate()
    objetos.append(OBJ("models/llantas_traseras.obj", swapyz=True))
    objetos[3].generate()

    for i in range(ncarros):
        carros.append(Carro(DimBoard, 1.0, 10.0))
        carros[-1].getComponents(objetos)

    # textura_piso = cargar_textura('piso.png')


# Se mueve al observador circularmente al rededor del plano XZ a una altura fija (EYE_Y)


def lookat():
    global EYE_X, EYE_Z, radius
    rad = math.radians(theta)
    EYE_X = CENTER_X + radius * math.cos(rad)
    EYE_Z = CENTER_Z + radius * math.sin(rad)
    glLoadIdentity()
    gluLookAt(EYE_X, EYE_Y, EYE_Z, CENTER_X, CENTER_Y, CENTER_Z, UP_X, UP_Y, UP_Z)


def ajustar_zoom(delta):
    global radius, EYE_Y
    # Límites para no atravesar el centro ni alejarse más allá de ZFAR
    radius_min = 60.0
    radius_max = ZFAR / 2

    # Guardamos la proporción altura/distancia original (150 / 250 = 0.6)
    relacion_altura = 0.6

    radius = max(radius_min, min(radius_max, radius + delta))
    EYE_Y = radius * relacion_altura
    lookat()


def update():
    for car in carros:
        car.update(edificios, fuente)

def display():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    Axis()
    dibujar_piso()

    glColor3f(1.0, 1.0, 1.0)
    for ed in edificios:
        ed.draw()

    for f in fuente:
        f.draw()

    for car in carros:
        car.draw()


done = False
Init()
while not done:
    keys = pygame.key.get_pressed()
    # avanzar observador

    if keys[pygame.K_UP]:
        theta = (theta + 0.7) % 360
        lookat()
    if keys[pygame.K_RIGHT]:
        theta = (theta - 0.7) % 360
        lookat()
    # solo se controla el ultimo carrito en el array
    if keys[pygame.K_w]:
        carros[-1].setAvanza()
    if keys[pygame.K_a]:
        carros[-1].setRota("L")
    if keys[pygame.K_d]:
        carros[-1].setRota("R")

    # Control de órbita horizontal
    if keys[pygame.K_h]:
        theta = (theta + 0.7) % 360
        lookat()
    if keys[pygame.K_l]:
        theta = (theta - 0.7) % 360
        lookat()
    if keys[pygame.K_k]:
        ajustar_zoom(-5.0)  # Reduce el radio para acercar
        lookat()
    if keys[pygame.K_j]:
        ajustar_zoom(5.0)  # Aumenta el radio para alejar
        lookat()

    for event in pygame.event.get():
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                done = True

    update()
    display()

    pygame.display.flip()
    pygame.time.wait(5)

pygame.quit()
