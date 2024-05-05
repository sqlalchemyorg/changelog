import os
import re

from setuptools import setup


v = open(os.path.join(os.path.dirname(__file__), "changelog", "__init__.py"))
VERSION = (
    re.compile(r".*__version__ = [\"'](.*?)[\"']", re.S)
    .match(v.read())
    .group(1)
)
v.close()

readme = os.path.join(os.path.dirname(__file__), "README.rst")


setup(
    name="changelog",
    version=VERSION,
    description="Provides simple Sphinx markup to render changelog displays.",
    long_description=open(readme).read(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
        "Topic :: Documentation",
    ],
    keywords="Sphinx",
    author="Mike Bayer",
    author_email="mike@zzzcomputing.com",
    url="https://github.com/sqlalchemyorg/changelog",
    license="MIT",
    packages=["changelog"],
    install_requires=[
        "Sphinx>=4.0.0",
        "docutils",
        "looseversion",
    ],
    include_package_data=True,
    zip_safe=False,
    entry_points={"console_scripts": ["changelog = changelog.cmd:main"]},
)
