#clusterflunk/setup.py
import os
from setuptools import setup

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.md')).read()
CHANGES = open(os.path.join(here, 'CHANGES.md')).read()

requires = [
    'colander'
]

tests_require = requires + [
    'nose',
    'colander',
    'mock'
]

setup(name='soap',
      version='0.0.1',
      description='Serialization/deserialization library that supports relationships.',
      long_description=README + '\n\n' + CHANGES,
      install_requires=requires,
      tests_require=tests_require,
      packages=['soap'],
      test_suite='soap.tests'
)
