"""Figuras básicas de OpenGL que comparten edificios, decoración y semáforos."""

from OpenGL.GL import *
from OpenGL.GLU import *

_quadric = None


def quadric():
    # Un solo objeto GLU para dibujar todos los cilindros y esferas
    global _quadric
    if _quadric is None:
        _quadric = gluNewQuadric()
    return _quadric


def caja(x0, y0, z0, x1, y1, z1):
    """Caja alineada con los ejes, de la esquina (x0, y0, z0) a (x1, y1, z1)."""
    caras = [
        ((0, 1, 0), [(x0, y1, z0), (x0, y1, z1), (x1, y1, z1), (x1, y1, z0)]),
        ((0, -1, 0), [(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)]),
        ((1, 0, 0), [(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)]),
        ((-1, 0, 0), [(x0, y0, z0), (x0, y0, z1), (x0, y1, z1), (x0, y1, z0)]),
        ((0, 0, 1), [(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]),
        ((0, 0, -1), [(x0, y0, z0), (x0, y1, z0), (x1, y1, z0), (x1, y0, z0)]),
    ]
    glBegin(GL_QUADS)
    for normal, vertices in caras:
        glNormal3f(*normal)
        for v in vertices:
            glVertex3f(*v)
    glEnd()


def cilindro(x, y, z, radio_abajo, radio_arriba, altura, lados=12):
    """Cilindro vertical que empieza en (x, y, z) y sube 'altura'."""
    glPushMatrix()
    glTranslatef(x, y, z)
    glRotatef(-90.0, 1.0, 0.0, 0.0)   # gluCylinder crece sobre Z; se gira para que crezca sobre Y
    gluCylinder(quadric(), radio_abajo, radio_arriba, altura, lados, 1)
    gluDisk(quadric(), 0.0, radio_abajo, lados, 1)
    glTranslatef(0.0, 0.0, altura)
    gluDisk(quadric(), 0.0, radio_arriba, lados, 1)
    glPopMatrix()


def esfera(x, y, z, radio, escala_y=1.0, lados=12):
    """Esfera; escala_y < 1 la aplana (arbustos, copas de árbol)."""
    glPushMatrix()
    glTranslatef(x, y, z)
    glScalef(1.0, escala_y, 1.0)
    gluSphere(quadric(), radio, lados, max(6, lados // 2))
    glPopMatrix()
