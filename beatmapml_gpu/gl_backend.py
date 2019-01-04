from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL import arrays
from slider.mod import circle_radius
import numpy as np
import ctypes

from .parameter_convert import calc_dimension, MAX_PLAYFIELD
from .shaders import *


class GLBackend():
    def __init__(self, width, cs, lookahead):
        self._canvas_size, self._field = calc_dimension(width)
        self._cs = circle_radius(cs)
        self._lookahead = lookahead

        self.init_matrix()
        self.init_context()
        self.init_gl()

    def init_context(self):
        import OpenGL
        platform = OpenGL.platform.PLATFORM
        try:
            import OpenGL.platform.egl
            OpenGL.platform.PLATFORM = OpenGL.platform.egl.EGLPlatform()
            import OpenGL.EGL as egl
            self._use_egl = True
            self.init_egl(egl)
        except ImportError as err:
            OpenGL.platform.PLATFORM = platform
            self._use_egl = False
            self.init_glut()

    def init_glut(self):
        import OpenGL.GLUT as glut
        glut.glutInit([''])
        glut.glutInitWindowSize(1, 1)
        glut.glutSetOption(glut.GLUT_ACTION_ON_WINDOW_CLOSE,
                           glut.GLUT_ACTION_GLUTMAINLOOP_RETURNS)
        glut.glutInitDisplayMode(glut.GLUT_SINGLE | glut.GLUT_RGBA)
        glut.glutCreateWindow(b"OpenGL Offscreen")
        glut.glutHideWindow()

    def init_egl(self, egl):
        DESIRED_ATTRIBUTES = [
            egl.EGL_SURFACE_TYPE, egl.EGL_PBUFFER_BIT,
            egl.EGL_RENDERABLE_TYPE, egl.EGL_OPENGL_BIT,
            egl.EGL_CONFIG_CAVEAT, egl.EGL_NONE,
            egl.EGL_NONE
        ]

        major, minor = ctypes.c_long(), ctypes.c_long()
        self._display = egl.eglGetDisplay(egl.EGL_DEFAULT_DISPLAY)
        egl.eglInitialize(self._display, major, minor)

        num_configs = ctypes.c_long()
        config = EGLConfig()
        attributes = arrays.GLintArray.asArray(DESIRED_ATTRIBUTES)
        egl.eglChooseConfig(self._display, attributes, config, 1, num_configs)
        egl.eglBindAPI(egl.EGL_OPENGL_API)

        ctx = egl.eglCreateContext(
            self._display, config, egl.EGL_NO_CONTEXT, None)
        egl.eglMakeCurrent(self._display, egl.EGL_NO_SURFACE,
                           egl.EGL_NO_SURFACE, ctx)

    def destroy(self):
        if self._use_egl:
            eglTerminate(self._display)

    def init_gl(self):
        glShadeModel(GL_SMOOTH)
        glDisable(GL_DEPTH_TEST)
        glDisable(GL_ALPHA_TEST)
        glClampColor(GL_CLAMP_READ_COLOR, GL_FALSE)
        glEnable(GL_BLEND)
        glBlendEquation(GL_FUNC_ADD)
        glBlendFunc(GL_ONE, GL_ONE)

        self.init_framebuffer()

        quad_vbo = np.array([[-1.0, -1.0],
                             [1.0, -1.0],
                             [-1.0, 1.0],
                             [-1.0, 1.0],
                             [1.0, -1.0],
                             [1.0, 1.0]], dtype=np.float32)
        self._quad_vboid = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, self._quad_vboid)
        glBufferData(GL_ARRAY_BUFFER, quad_vbo.nbytes,
                     quad_vbo, GL_STATIC_DRAW)
        self._quad_vaoid = glGenVertexArrays(1)
        self.init_shaders()

    def init_shaders(self):
        self.init_disk_shader()
        self.init_avg_shader()

    def init_disk_shader(self):
        vertexID = self.compileShader(DISK_VERTEX_SHADER,
                                      GL_VERTEX_SHADER)
        geometryID = self.compileShader(DISK_GEOMETRY_SHADER,
                                        GL_GEOMETRY_SHADER)
        fragmentID = self.compileShader(DISK_FRAGMENT_SHADER,
                                        GL_FRAGMENT_SHADER)
        self._disk_program = glCreateProgram()
        glAttachShader(self._disk_program, vertexID)
        glAttachShader(self._disk_program, geometryID)
        glAttachShader(self._disk_program, fragmentID)
        glLinkProgram(self._disk_program)

        if glGetProgramiv(self._disk_program, GL_LINK_STATUS) != GL_TRUE:
            raise RuntimeError(glGetProgramInfoLog(
                self._disk_program).decode())

        glDetachShader(self._disk_program, vertexID)
        glDetachShader(self._disk_program, geometryID)
        glDetachShader(self._disk_program, fragmentID)

        glDeleteShader(vertexID)
        glDeleteShader(geometryID)
        glDeleteShader(fragmentID)

        glUseProgram(self._disk_program)
        self._disk_tick_uniform = glGetUniformLocation(
            self._disk_program, 'tick')
        lookahead_uniform = glGetUniformLocation(
            self._disk_program, 'lookahead')
        glUniform1f(lookahead_uniform, self._lookahead)
        radius_uniform = glGetUniformLocation(
            self._disk_program, 'radius')
        glUniform1f(radius_uniform, self._cs)
        osu2canvas_uniform = glGetUniformLocation(
            self._disk_program, 'osuToCanvas')
        glUniformMatrix4fv(osu2canvas_uniform, 1, True, self._osu_to_canvas)
        projection_uniform = glGetUniformLocation(
            self._disk_program, 'projection')
        glUniformMatrix4fv(projection_uniform, 1, True, self._projection)

    def init_avg_shader(self):
        vertexID = self.compileShader(AVG_VERTEX_SHADER,
                                      GL_VERTEX_SHADER)
        fragmentID = self.compileShader(AVG_FRAGMENT_SHADER,
                                        GL_FRAGMENT_SHADER)
        self._avg_program = glCreateProgram()
        glAttachShader(self._avg_program, vertexID)
        glAttachShader(self._avg_program, fragmentID)
        glLinkProgram(self._avg_program)

        if glGetProgramiv(self._avg_program, GL_LINK_STATUS) != GL_TRUE:
            raise RuntimeError(glGetProgramInfoLog(
                self._avg_program).decode())

        glDetachShader(self._avg_program, vertexID)
        glDetachShader(self._avg_program, fragmentID)

        glDeleteShader(vertexID)
        glDeleteShader(fragmentID)
        glUseProgram(self._avg_program)
        glBindBuffer(GL_ARRAY_BUFFER, self._quad_vboid)
        glBindVertexArray(self._quad_vaoid)

        avg_position_attrib = glGetAttribLocation(
            self._avg_program, 'position')
        glEnableVertexAttribArray(avg_position_attrib)
        glVertexAttribPointer(avg_position_attrib,
                              2, GL_FLOAT, GL_FALSE, 0, None)

        self._avg_sampler_uniform = glGetUniformLocation(
            self._avg_program, 'avgSampler')

    def compileShader(self, source, type):
        shader = glCreateShader(type)
        glShaderSource(shader, source)
        glCompileShader(shader)
        if glGetShaderiv(shader, GL_COMPILE_STATUS) != GL_TRUE:
            raise RuntimeError(glGetShaderInfoLog(shader).decode())
        return shader

    def init_framebuffer(self):
        self._framebuffer = glGenFramebuffers(1)
        glBindFramebuffer(GL_FRAMEBUFFER, self._framebuffer)
        self._texture = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self._texture)
        glTexStorage2D(GL_TEXTURE_2D, 1, GL_RG32F,
                       self._canvas_size.w, self._canvas_size.h)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0,
                               GL_TEXTURE_2D, self._texture, 0)
        draw_buffer = np.array([GL_COLOR_ATTACHMENT0], dtype=np.uint32)
        glDrawBuffers(draw_buffer)
        if glCheckFramebufferStatus(GL_FRAMEBUFFER) != GL_FRAMEBUFFER_COMPLETE:
            raise RuntimeError("Cannot initiate framebuffer as texture")

        self._result_framebuffer = glGenFramebuffers(1)
        glBindFramebuffer(GL_FRAMEBUFFER, self._result_framebuffer)
        result_texture = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, result_texture)
        glTexStorage2D(GL_TEXTURE_2D, 1, GL_R32F,
                       self._canvas_size.w, self._canvas_size.h)
        glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0,
                               GL_TEXTURE_2D, result_texture, 0)
        draw_buffer = np.array([GL_COLOR_ATTACHMENT0], dtype=np.uint32)
        glDrawBuffers(draw_buffer)
        if glCheckFramebufferStatus(GL_FRAMEBUFFER) != GL_FRAMEBUFFER_COMPLETE:
            raise RuntimeError("Cannot initiate framebuffer as texture")

    def init_matrix(self):
        (l, t, r, b) = self._field
        self._osu_to_canvas = np.array([[(r - l) / MAX_PLAYFIELD[0], 0, 0, l],
                                        [0, (b - t) / MAX_PLAYFIELD[1], 0, t],
                                        [0, 0, 1, 0],
                                        [0, 0, 0, 1]], dtype=np.float32)
        (w, h) = self._canvas_size
        self._projection = np.array([[2 / w, 0, 0, -1],
                                     [0, -2 / h, 0, 1],
                                     [0, 0, 1, 0],
                                     [0, 0, 0, 1]], dtype=np.float32)

    def equip_circles(self, hitcircles):
        vbo = np.array([[c.position.x,
                         c.position.y,
                         c.time_ms]
                        for c in hitcircles], dtype=np.float32)
        self._circle_vboid = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, self._circle_vboid)
        glBufferData(GL_ARRAY_BUFFER, vbo.nbytes, vbo, GL_STATIC_DRAW)

        self._circle_vaoid = glGenVertexArrays(1)
        glBindVertexArray(self._circle_vaoid)

        disk_position_attrib = glGetAttribLocation(
            self._disk_program, 'position')
        disk_activation_attrib = glGetAttribLocation(
            self._disk_program, 'activationTime')

        glEnableVertexAttribArray(disk_position_attrib)
        glEnableVertexAttribArray(disk_activation_attrib)
        glVertexAttribPointer(disk_position_attrib,
                              2, GL_FLOAT, GL_FALSE, 12, None)
        glVertexAttribPointer(disk_activation_attrib,
                              1, GL_FLOAT, GL_FALSE, 12, ctypes.c_void_p(8))

    def setup(self):
        glBindFramebuffer(GL_FRAMEBUFFER, self._framebuffer)
        glViewport(0, 0, self._canvas_size.w, self._canvas_size.h)
        glClear(GL_COLOR_BUFFER_BIT)

    def render_circles(self, tick, start, end):
        glUseProgram(self._disk_program)
        glBindBuffer(GL_ARRAY_BUFFER, self._circle_vboid)
        glBindVertexArray(self._circle_vaoid)

        glUniform1f(self._disk_tick_uniform, tick)
        glDrawArrays(GL_POINTS, start, end - start)

    def calc_avg(self):
        glFinish()
        glBindFramebuffer(GL_FRAMEBUFFER, self._result_framebuffer)
        glViewport(0, 0, self._canvas_size.w, self._canvas_size.h)
        glClear(GL_COLOR_BUFFER_BIT)
        glUseProgram(self._avg_program)
        glBindBuffer(GL_ARRAY_BUFFER, self._quad_vboid)
        glBindVertexArray(self._quad_vaoid)

        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, self._texture)
        glUniform1i(self._avg_sampler_uniform, 0)

        glDrawArrays(GL_TRIANGLES, 0, 6)
        glFinish()

        return self.read_pixels()

    def read_pixels(self):
        buf = glReadPixels(0, 0,
                           self._canvas_size.w,
                           self._canvas_size.h,
                           GL_RED, GL_FLOAT)
        return buf.reshape((self._canvas_size.h,
                            self._canvas_size.w)).transpose()
