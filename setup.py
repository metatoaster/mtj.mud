from setuptools import setup, find_packages
import sys, os

version = '0'

setup(name='mtmud',
      version=version,
      description="Basic Mud Package",
      long_description="""\
""",
      classifiers=[], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
      keywords='MUD',
      author='Tommy Yu',
      author_email='y@metatoaster.com',
      url='',
      license='GPL',
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
