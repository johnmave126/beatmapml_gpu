import os

USE_EGL = False

if os.name != 'nt':
    os.environ['PYOPENGL_PLATFORM'] = 'egl'
    USE_EGL = True
