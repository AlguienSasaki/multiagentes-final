from OpenGL.GL import *

class Fuente:
    def __init__(self, obj_model, pos, scale=(1.0, 1.0, 1.0)):
        self.model = obj_model
        self.Position = [float(pos[0]), float(pos[1]), float(pos[2])]
        self.scale = scale

        self.dim_x = 0.18
        self.dim_z = 0.18

        self.half_x = (self.dim_x * self.scale[0]) / 2.0
        self.half_z = (self.dim_z * self.scale[2]) / 2.0

        self.min_x = self.Position[0] - self.half_x
        self.max_x = self.Position[0] + self.half_x
        self.min_z = self.Position[2] - self.half_z
        self.max_z = self.Position[2] + self.half_z
    ##############################################
    def colisiona_con(self, x, z, radio):
        return (
            x + radio > self.min_x and
            x - radio < self.max_x and
            z + radio > self.min_z and
            z - radio < self.max_z
        )

    def draw(self):
        glPushMatrix()
        glTranslatef(self.Position[0], self.Position[1], self.Position[2])
        glScalef(self.scale[0], self.scale[1], self.scale[2])
        glTranslatef(-0.355, 0.0, -0.501)
        self.model.render()
        glPopMatrix()
