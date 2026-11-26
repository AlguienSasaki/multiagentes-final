"""Simulación gráfica de la ciudad (Pygame + PyOpenGL). Solo dibuja el estado
que calcula ModeloTrafico (AgentPy). Los controles están en procesar_tecla(),
mover_camara() y en el README."""

import os
import math

import pygame
from pygame.locals import *

from OpenGL.GL import *
from OpenGL.GLU import *

from Carro import Carro
from Fuente import Fuente
from Semaforo import Semaforo
from Escenario import crear_escenario
from objloader import OBJ
from modelo_multiagentes import ModeloTrafico, DT, ESCENARIOS, M

# Rutas relativas a este archivo (funciona sin importar desde dónde se ejecute)
BASE = os.path.dirname(os.path.abspath(__file__))


def ruta(*partes):
    return os.path.join(BASE, *partes)


# Dimension del plano
DimBoard = 1800
screen_width = 1200
screen_height = 700
# vc para el obser.
FOVY = 60.0
ZNEAR = 10.0
ZFAR = 9000.0
CENTER_X = DimBoard / 2.0
CENTER_Y = 0
CENTER_Z = DimBoard / 2.0
COLOR_CIELO = (0.62, 0.80, 0.95)

ESCALA_CARRO = 6.0
# Colores de carrocería; cada carro toma uno según su id
COLORES_CARRO = [
    (0.75, 0.10, 0.10), (0.10, 0.30, 0.75), (0.92, 0.92, 0.90), (0.95, 0.75, 0.10),
    (0.15, 0.55, 0.25), (0.12, 0.12, 0.14), (0.95, 0.45, 0.10), (0.62, 0.64, 0.68),
    (0.10, 0.55, 0.60), (0.50, 0.15, 0.45),
]

# Objetos gráficos
objetos = []            # componentes del carro (se cargan una sola vez)
listas_carroceria = []  # una lista de OpenGL por color
carros = {}             # id del agente -> Carro
fuente = None
semaforos = []
lista_escenario = None  # edificios y decoración compilados en una lista de OpenGL

# Variables para el control del observador
theta = 65.0
radius = 2300.0
altura_camara = 0.55    # altura del ojo = radius * altura_camara
vista_superior = False
textura_piso = None

# Para aspect ratio de la imagen del piso
ANCHO_X = DimBoard
LARGO_Z = DimBoard

# Estado de la simulación
modelo = None
n_vehiculos = ESCENARIOS["moderado"]
politica = "adaptativa"
semilla = 2026
pausa = False


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
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, ancho, alto, 0, GL_RGBA, GL_UNSIGNED_BYTE, datos_imagen)
    return tex_id, ancho, alto


def dibujar_piso():
    # Pasto alrededor de la ciudad, un poco más abajo. El color es el verde de
    # piso.png dividido entre la iluminación total (≈1.13) para que se vea igual.
    glColor3f(0.66, 0.74, 0.42)
    glBegin(GL_QUADS)
    glNormal3f(0.0, 1.0, 0.0)
    glVertex3d(-4000, -10.5, -4000)
    glVertex3d(-4000, -10.5, LARGO_Z + 4000)
    glVertex3d(ANCHO_X + 4000, -10.5, LARGO_Z + 4000)
    glVertex3d(ANCHO_X + 4000, -10.5, -4000)
    glEnd()

    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, textura_piso)
    glColor3f(1.0, 1.0, 1.0)
    altura_piso = -10.0
    # La parte superior de la imagen queda en z = 0. Así un pixel (u, v) de
    # piso.png corresponde al punto (u, v) * 5/3 del mundo y la red vial
    # (red_vial.py) coincide exactamente con las calles dibujadas.
    glBegin(GL_QUADS)
    glNormal3f(0.0, 1.0, 0.0)
    glTexCoord2f(0.0, 1.0)
    glVertex3d(0.0, altura_piso, 0.0)
    glTexCoord2f(0.0, 0.0)
    glVertex3d(0.0, altura_piso, LARGO_Z)
    glTexCoord2f(1.0, 0.0)
    glVertex3d(ANCHO_X, altura_piso, LARGO_Z)
    glTexCoord2f(1.0, 1.0)
    glVertex3d(ANCHO_X, altura_piso, 0.0)
    glEnd()
    glBindTexture(GL_TEXTURE_2D, 0)
    glDisable(GL_TEXTURE_2D)


def configurar_luces():
    # Sol (luz direccional inclinada para que las fachadas tengan sombreado)
    glLightfv(GL_LIGHT0, GL_POSITION, (-0.5, 1.0, 0.7, 0.0))
    glLightfv(GL_LIGHT0, GL_AMBIENT, (0.30, 0.32, 0.36, 1.0))
    glLightfv(GL_LIGHT0, GL_DIFFUSE, (0.72, 0.70, 0.64, 1.0))
    # Luz de relleno desde el lado opuesto, más débil
    glLightfv(GL_LIGHT1, GL_POSITION, (0.6, 0.5, -0.8, 0.0))
    glLightfv(GL_LIGHT1, GL_AMBIENT, (0.0, 0.0, 0.0, 1.0))
    glLightfv(GL_LIGHT1, GL_DIFFUSE, (0.20, 0.22, 0.26, 1.0))
    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)
    glEnable(GL_LIGHT1)
    glEnable(GL_COLOR_MATERIAL)
    glEnable(GL_NORMALIZE)
    # Niebla del color del cielo para que el horizonte se vea suave
    glEnable(GL_FOG)
    glFogi(GL_FOG_MODE, GL_LINEAR)
    glFogfv(GL_FOG_COLOR, (*COLOR_CIELO, 1.0))
    glFogf(GL_FOG_START, 4500.0)
    glFogf(GL_FOG_END, 8500.0)


def Init():
    global textura_piso, ANCHO_X, LARGO_Z, CENTER_X, CENTER_Z, fuente, lista_escenario

    # 1. PRIMERO crear la ventana y el contexto OpenGL
    pygame.display.set_mode((screen_width, screen_height), DOUBLEBUF | OPENGL)
    pygame.display.set_caption("Simulación de tráfico multiagentes")
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(FOVY, screen_width / screen_height, ZNEAR, ZFAR)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()

    # 2. SEGUNDO cargar la textura y calcular las dimensiones reales del mapa
    textura_piso, img_ancho, img_alto = cargar_textura(ruta("piso.png"))
    aspect_ratio = img_ancho / float(img_alto)
    LARGO_Z = DimBoard
    ANCHO_X = DimBoard * aspect_ratio
    CENTER_X = ANCHO_X / 2.0
    CENTER_Z = LARGO_Z / 2.0

    lookat()
    glClearColor(*COLOR_CIELO, 1.0)
    glEnable(GL_DEPTH_TEST)
    glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
    glShadeModel(GL_SMOOTH)
    configurar_luces()

    # 3. TERCERO cargar los modelos .obj una sola vez
    # (OBJ ya genera su lista de OpenGL al crearse)
    modelo_edificio = OBJ(ruta("models", "edificio.obj"), swapyz=False)
    modelo_fuente = OBJ(ruta("models", "fuente.obj"), swapyz=False)
    fuente = Fuente(modelo_fuente, (CENTER_X, -10.0, CENTER_Z), scale=(800.0, 800.0, 800.0))

    objetos.clear()
    for nombre in ("carroceria.obj", "llanta_FL.obj", "llanta_FR.obj", "llantas_traseras.obj"):
        objetos.append(OBJ(ruta("models", nombre), swapyz=True))
    # Una lista de la carrocería por cada color (los materiales .001 y .012 son la pintura)
    carroceria = objetos[0]
    listas_carroceria.clear()
    for color in COLORES_CARRO:
        carroceria.mtl["Material.001"]["Kd"] = color
        carroceria.mtl["Material.012"]["Kd"] = color
        carroceria.generate()
        listas_carroceria.append(carroceria.gl_list)

    # Los objetos que no se mueven se compilan una sola vez en una lista
    lista_escenario = glGenLists(1)
    glNewList(lista_escenario, GL_COMPILE)
    for objeto in crear_escenario(modelo_edificio, ANCHO_X, LARGO_Z):
        objeto.draw()
    glEndList()

    crear_modelo()


def crear_modelo():
    """Crea (o reinicia) el modelo AgentPy y los objetos gráficos ligados a él."""
    global modelo, pausa
    modelo = ModeloTrafico({"n_vehiculos": n_vehiculos, "politica": politica})
    modelo.sim_setup(seed=semilla)          # sin 'steps': corre hasta cerrar la ventana
    carros.clear()
    for agente in modelo.vehiculos:
        lista = listas_carroceria[agente.id % len(listas_carroceria)]
        carro = Carro(objetos, ESCALA_CARRO, lista)
        carro.sincronizar(agente, 1.0)
        carros[agente.id] = carro
    semaforos.clear()
    for nombre_inter, acceso, x, z in modelo.red.postes:
        semaforos.append(Semaforo(x, z, modelo.inter[nombre_inter].semaforo, acceso))
    pausa = False


# Se mueve al observador circularmente al rededor del plano XZ
def lookat():
    glLoadIdentity()
    if vista_superior:
        # Vista desde arriba: el norte del mapa queda en la parte superior
        gluLookAt(CENTER_X, radius * 1.15, CENTER_Z + 0.01, CENTER_X, CENTER_Y, CENTER_Z, 0, 0, -1)
        return
    rad = math.radians(theta)
    eye_x = CENTER_X + radius * math.cos(rad)
    eye_z = CENTER_Z + radius * math.sin(rad)
    eye_y = radius * altura_camara
    gluLookAt(eye_x, eye_y, eye_z, CENTER_X, CENTER_Y, CENTER_Z, 0, 1, 0)


def ajustar_zoom(delta):
    global radius
    # Límites para no atravesar el centro ni salir de la niebla
    radius = max(150.0, min(4200.0, radius + delta))
    lookat()


def ajustar_altura(delta):
    global altura_camara
    altura_camara = max(0.08, min(1.6, altura_camara + delta))
    lookat()


def display(alpha):
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    dibujar_piso()
    glCallList(lista_escenario)
    fuente.draw(modelo.tiempo)
    for s in semaforos:
        s.draw()
    for agente in modelo.vehiculos:
        carro = carros[agente.id]
        carro.sincronizar(agente, alpha)
        carro.draw()


def actualizar_titulo():
    vel = sum(v.velocidad for v in modelo.vehiculos) / max(1, len(modelo.vehiculos)) / M
    cruces = sum(i.cruces for i in modelo.intersecciones)
    detenidos = sum(1 for v in modelo.vehiculos if v.estado == "ESPERAR")
    texto = (f"Tráfico | t={modelo.tiempo:5.0f} s | {len(modelo.vehiculos)} vehículos | "
             f"política {modelo.p.politica} | vel. media {vel:4.1f} m/s | detenidos {detenidos} | "
             f"cruces {cruces} | choques {modelo.contadores['colisiones']}")
    if pausa:
        texto += " | PAUSA"
    pygame.display.set_caption(texto)


def guardar_captura(archivo=None):
    """Guarda lo que se ve en la ventana como imagen PNG."""
    if archivo is None:
        carpeta = ruta("capturas")
        os.makedirs(carpeta, exist_ok=True)
        archivo = os.path.join(carpeta, f"captura_{pygame.time.get_ticks()}.png")
    glPixelStorei(GL_PACK_ALIGNMENT, 1)
    datos = glReadPixels(0, 0, screen_width, screen_height, GL_RGB, GL_UNSIGNED_BYTE)
    imagen = pygame.image.frombuffer(datos, (screen_width, screen_height), "RGB")
    # OpenGL lee las filas de abajo hacia arriba
    pygame.image.save(pygame.transform.flip(imagen, False, True), archivo)
    print("Captura guardada en", archivo)
    return archivo


def procesar_tecla(tecla):
    """Teclas de un solo toque. Regresa False si hay que salir."""
    global pausa, n_vehiculos, politica, vista_superior
    if tecla == pygame.K_ESCAPE:
        return False
    if tecla == pygame.K_SPACE:
        pausa = not pausa
    elif tecla == pygame.K_r:
        crear_modelo()
    elif tecla in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
        n_vehiculos = min(60, n_vehiculos + 4)
        crear_modelo()
    elif tecla in (pygame.K_MINUS, pygame.K_KP_MINUS):
        n_vehiculos = max(1, n_vehiculos - 4)
        crear_modelo()
    elif tecla == pygame.K_1:
        n_vehiculos = ESCENARIOS["ligero"]
        crear_modelo()
    elif tecla == pygame.K_2:
        n_vehiculos = ESCENARIOS["moderado"]
        crear_modelo()
    elif tecla == pygame.K_3:
        n_vehiculos = ESCENARIOS["elevado"]
        crear_modelo()
    elif tecla == pygame.K_p:
        # Se cambia en vivo: los semáforos leen la política en cada paso
        politica = "fija" if modelo.p.politica == "adaptativa" else "adaptativa"
        modelo.p.politica = politica
    elif tecla == pygame.K_v:
        vista_superior = not vista_superior
        lookat()
    elif tecla == pygame.K_F12:
        guardar_captura()
    return True


def mover_camara():
    """Teclas que se mantienen presionadas."""
    global theta
    keys = pygame.key.get_pressed()
    if keys[pygame.K_UP] or keys[pygame.K_LEFT] or keys[pygame.K_h]:
        theta = (theta + 0.7) % 360
        lookat()
    if keys[pygame.K_RIGHT] or keys[pygame.K_l]:
        theta = (theta - 0.7) % 360
        lookat()
    if keys[pygame.K_k]:
        ajustar_zoom(-15.0)
    if keys[pygame.K_j]:
        ajustar_zoom(15.0)
    if keys[pygame.K_w]:
        ajustar_altura(0.01)
    if keys[pygame.K_s]:
        ajustar_altura(-0.01)


def main():
    pygame.init()
    Init()
    reloj = pygame.time.Clock()
    acumulado = 0.0
    cuadros = 0
    done = False
    while not done:
        dt_real = min(reloj.tick(60) / 1000.0, 0.25)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                done = True
            elif event.type == pygame.KEYDOWN:
                if not procesar_tecla(event.key):
                    done = True
            elif event.type == pygame.MOUSEWHEEL:
                ajustar_zoom(-80.0 * event.y)
        mover_camara()

        # Paso lógico fijo: la simulación avanza DT segundos por paso sin
        # importar los FPS; alpha sirve para interpolar el dibujo.
        if not pausa:
            acumulado += dt_real
            while acumulado >= DT:
                modelo.sim_step()
                acumulado -= DT
        display(acumulado / DT)
        pygame.display.flip()

        cuadros += 1
        if cuadros % 15 == 0:
            actualizar_titulo()

    pygame.quit()


if __name__ == "__main__":
    main()
