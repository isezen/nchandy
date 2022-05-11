# pylint: disable=C0103
"""
nchandy.

~~~~~~~~~
Handy NetCDF tools to work with NetCDF files
"""
import os
import pathlib
from setuptools import setup, find_packages


def get(x):
    """Get library properties from __init__.py."""
    with open(
        os.path.join(
            os.path.dirname(__file__),
            'nchandy', '__init__.py'), encoding="utf-8") as f:
        for line in f.readlines():
            if line.startswith('__' + x + '__'):
                return line.split('=')[1].strip()[1:-1]
    return None


here = pathlib.Path(__file__).parent.resolve()
long_description = (here / "README.md").read_text(encoding="utf-8")

dependencies = [
    "numpy",
    "xarray",
    "netCDF4",
    "aiofiles==0.7.0",  # Async IO for files
    "colorama==0.4.4",  # Colorizes terminal output
    "colorlog==6.6.0",  # Adds color to logs
    "concurrent-log-handler==0.9.19",  # Concurrently log and rotate logs
    "click",  # For the CLI
]

setup(
    name='nchandy',
    version=get('version'),
    platforms=['linux', 'darwin'],
    packages=find_packages(),
    package_dir={'nchandy': 'nchandy'},
    include_package_data=True,
    setup_requires=['pytest-runner'],
    install_requires=dependencies,
    tests_require=['pytest'],
    scripts=[],
    entry_points={
        'console_scripts': [
            'nch=nchandy._cmds_:main'],
    },
    author=get('author'),
    author_email=get('email'),
    description='Handy tools to work with NetCDF files',
    long_description=long_description,
    long_description_content_type="text/markdown",
    license=get('license'),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Operating System :: OS dependent",
        "License :: OSI Approved :: AGPL v3.0 License",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3 :: Only",
        "Topic :: Utilities",
    ],
    python_requires=">=3.7, <4",
    keywords=['netcdf', 'WMO', 'ecCodes'],
    project_urls={  # Optional
        "Bug Reports": "https://github.com/isezen/nchandy/issues",
        "Source": "https://github.com/isezen/nchandy/",
    },
    url='https://github.com/isezen/nchandy',
)
