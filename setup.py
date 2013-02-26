from setuptools import setup, find_packages
import sys, os

version = '0'

setup(name='mtj.mud',
      version=version,
      description="MTJ Mud Engine",
      long_description="""""",
      classifiers=[], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
      keywords='MUD',
      author='Tommy Yu',
      author_email='y@metatoaster.com',
      url='https://github.com/metatoaster/mtj.mud',
      license='GPL',
      scripts=['mudctrl'],
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          # -*- Extra requirements: -*-
      ],
      entry_points="""
      # -*- Entry points: -*-
      """,
      )
