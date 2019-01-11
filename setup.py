#!/usr/bin/env python
from setuptools import setup, find_packages


setup(
    name='beatmapml_gpu',
    version='0.2.3',
    description=('Utilities for osu! beatmap in machine '
                 'learning, GPU accelerated'),
    author='Youmu Chan',
    author_email='johnmave126@gmail.com',
    packages=find_packages(),
    license='MIT',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3 :: Only',
        'Topic :: Games/Entertainment',
    ],
    url='https://github.com/johnmave126/beatmapml',
    install_requires=[
        'numpy',
        'bezier',
        'pyopengl',
        'pyopengl_accelerate',
        ('slider @ git+https://github.com/llllllllll/slider.git@'
         'master#egg=slider-0.1.0')
    ]
)
