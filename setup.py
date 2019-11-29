from setuptools import setup, find_packages
from os import path

here = path.abspath(path.dirname(__file__))

setup(

    packages=find_packages(exclude=['contrib', 'docs', 'tests']),  # Required
    pbr=True,
    setup_requires=['pbr>=1.9', 'setuptools>=17.1']
)
