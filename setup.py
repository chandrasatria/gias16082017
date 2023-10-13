from setuptools import setup, find_packages

with open('requirements.txt') as f:
	install_requires = f.read().strip().split('\n')

# get version from __version__ variable in addons/__init__.py
from addons import __version__ as version

setup(
	name='addons',
	version=version,
	description='addons',
	author='das',
	author_email='das@gmail.com',
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
