"""Ubicación de edificios y decoración, en pixeles de piso.png (como red_vial.py).
Todo va en áreas verdes o banquetas, nunca sobre el asfalto."""

import math

from red_vial import ESCALA
from Edificio import Edificio, EdificioUrbano
from Decoracion import Arbol, Arbusto, Jardin, Banca, Farola

# Áreas verdes de cada manzana medidas en piso.png: (u0, v0, u1, v1)
MANZANAS = {
    "NO": (141, 131, 884, 459),
    "NE": (1037, 131, 1781, 459),
    "SO": (142, 615, 884, 949),
    "SE": (1038, 615, 1781, 949),
}

# Colores de fachada
TERRACOTA = (0.80, 0.52, 0.40)
CREMA = (0.93, 0.87, 0.72)
AZUL_GRIS = (0.60, 0.68, 0.78)
LADRILLO = (0.70, 0.36, 0.30)
VERDE_GRIS = (0.62, 0.72, 0.64)
ARENA = (0.86, 0.76, 0.58)

# Edificios por manzana, siguiendo la distribución del diseño M4.
# (u0, v0, u1, v1) en fracciones de la manzana, pisos, color y fachada con puerta.
EDIFICIOS = {
    "NO": [((0.05, 0.08, 0.40, 0.72), 7, TERRACOTA, "S"),      # edificio en L (parte alta)
           ((0.40, 0.35, 0.62, 0.72), 4, ARENA, "S"),          # edificio en L (parte baja)
           ((0.70, 0.10, 0.92, 0.55), 5, AZUL_GRIS, "S")],
    "NE": [((0.68, 0.38, 0.92, 0.85), 6, CREMA, "S")],         # + edificio original (OBJ)
    "SO": [((0.06, 0.22, 0.28, 0.72), 5, VERDE_GRIS, "N"),
           ((0.35, 0.45, 0.85, 0.78), 3, CREMA, "N"),          # edificio en L (parte baja)
           ((0.55, 0.12, 0.85, 0.45), 8, AZUL_GRIS, "N")],     # edificio en L (parte alta)
    "SE": [((0.06, 0.40, 0.42, 0.75), 4, LADRILLO, "N"),
           ((0.55, 0.10, 0.92, 0.45), 9, ARENA, "N"),          # edificio en L (parte alta)
           ((0.70, 0.45, 0.92, 0.85), 5, TERRACOTA, "N")],     # edificio en L (parte baja)
}

# Árboles (u, v, pino) en fracciones de la manzana
ARBOLES = {
    "NO": [(0.12, 0.88, False), (0.26, 0.90, False), (0.42, 0.88, True), (0.56, 0.90, False),
           (0.70, 0.88, False), (0.80, 0.68, True), (0.95, 0.10, False), (0.50, 0.12, False)],
    "NE": [(0.30, 0.88, False), (0.42, 0.90, True), (0.55, 0.88, False), (0.95, 0.12, False),
           (0.80, 0.12, True), (0.64, 0.14, False), (0.96, 0.90, False)],
    "SO": [(0.10, 0.90, False), (0.25, 0.92, True), (0.40, 0.90, False), (0.55, 0.92, False),
           (0.70, 0.90, True), (0.10, 0.08, False), (0.35, 0.10, False), (0.92, 0.90, False)],
    "SE": [(0.30, 0.90, False), (0.45, 0.92, True), (0.60, 0.90, False), (0.10, 0.12, False),
           (0.30, 0.12, True), (0.45, 0.20, False), (0.96, 0.92, False)],
}

# Jardineras (u0, v0, u1, v1) y bancas (u, v, angulo)
JARDINES = {
    "NO": [(0.46, 0.10, 0.62, 0.25)],
    "NE": [(0.10, 0.80, 0.24, 0.94)],
    "SO": [(0.30, 0.82, 0.48, 0.94)],
    "SE": [(0.10, 0.82, 0.26, 0.94), (0.60, 0.55, 0.66, 0.85)],
}
BANCAS = {
    "NO": [(0.19, 0.93, 180), (0.63, 0.93, 180)],
    "NE": [(0.36, 0.93, 180), (0.62, 0.93, 180)],
    "SO": [(0.18, 0.06, 0), (0.48, 0.06, 0)],
    "SE": [(0.38, 0.06, 0), (0.68, 0.06, 0)],
}


def _a_mundo(u, v):
    return u * ESCALA, v * ESCALA


def _en_manzana(nombre, fu, fv):
    u0, v0, u1, v1 = MANZANAS[nombre]
    return _a_mundo(u0 + fu * (u1 - u0), v0 + fv * (v1 - v0))


def _farolas():
    """Farolas sobre las banquetas, con el brazo hacia la calle."""
    farolas = []

    def agregar(u, v, hacia_u, hacia_v):
        x, z = _a_mundo(u, v)
        angulo = math.degrees(math.atan2(-hacia_v, hacia_u))
        farolas.append(Farola(x, z, angulo))

    # Banqueta interior del circuito (se saltan las esquinas y las bocacalles)
    for u in range(260, 1700, 230):
        if abs(u - 960) > 110:
            agregar(u, 118, 0, -1)
            agregar(u, 963, 0, 1)
    for v in (260, 400, 690, 830):
        agregar(128, v, -1, 0)
        agregar(1794, v, 1, 0)
    # Banquetas de las calles interiores
    for v in (170, 300, 780, 910):
        agregar(895, v, 1, 0)
        agregar(1026, v, -1, 0)
    for u in (220, 440, 660, 1260, 1480, 1700):
        agregar(u, 475, 0, 1)
        agregar(u, 600, 0, -1)
    return farolas


def _arboles_alrededor(ancho, largo):
    """Árboles fuera del mapa para que la ciudad no se vea flotando."""
    arboles = []
    k = 0
    paso = 260.0
    x = -350.0
    while x <= ancho + 350:
        for z in (-180.0, -420.0, largo + 180.0, largo + 420.0):
            arboles.append(Arbol(x + (k % 3) * 40, z, 110 + (k % 4) * 20, pino=k % 3 == 0, tono=k))
            k += 1
        x += paso
    z = -100.0
    while z <= largo + 100:
        for x in (-180.0, -420.0, ancho + 180.0, ancho + 420.0):
            arboles.append(Arbol(x, z + (k % 3) * 40, 110 + (k % 4) * 20, pino=k % 2 == 0, tono=k))
            k += 1
        z += paso
    return arboles


def crear_escenario(modelo_edificio, ancho, largo):
    """Regresa la lista de objetos estáticos que se dibujan en la ciudad."""
    objetos = []
    for nombre, lista in EDIFICIOS.items():
        for (fu0, fv0, fu1, fv1), pisos, color, puerta in lista:
            x0, z0 = _en_manzana(nombre, fu0, fv0)
            x1, z1 = _en_manzana(nombre, fu1, fv1)
            objetos.append(EdificioUrbano(x0, z0, x1, z1, pisos, color, puerta))

    # Edificio original (OBJ) en la manzana NE, girado 90° y con escala uniforme
    x, z = _en_manzana("NE", 0.32, 0.38)
    objetos.append(Edificio(x, -10.0, z, (17.0, 17.0, 17.0), modelo_edificio, 90.0))

    k = 0
    for nombre, lista in ARBOLES.items():
        for fu, fv, pino in lista:
            x, z = _en_manzana(nombre, fu, fv)
            objetos.append(Arbol(x, z, 75 + (k % 3) * 15, pino, k))
            k += 1
    for nombre, lista in JARDINES.items():
        for fu0, fv0, fu1, fv1 in lista:
            x0, z0 = _en_manzana(nombre, fu0, fv0)
            x1, z1 = _en_manzana(nombre, fu1, fv1)
            objetos.append(Jardin(x0, z0, x1, z1))
    for nombre, lista in BANCAS.items():
        for fu, fv, angulo in lista:
            x, z = _en_manzana(nombre, fu, fv)
            objetos.append(Banca(x, z, angulo))
    # Arbustos con flores junto a los edificios
    flores = [(0.95, 0.35, 0.55), None, (1.0, 0.85, 0.3), None]
    for nombre in MANZANAS:
        for i, (fu, fv) in enumerate(((0.03, 0.78), (0.33, 0.78), (0.64, 0.80), (0.94, 0.62))):
            if nombre.startswith("S"):
                fv = 1.0 - fv
            x, z = _en_manzana(nombre, fu, fv)
            objetos.append(Arbusto(x, z, 14.0, flores[i]))

    objetos += _farolas()
    objetos += _arboles_alrededor(ancho, largo)
    return objetos
