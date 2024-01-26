# -*- coding: utf-8 -*-


"""setup.py: setuptools control."""


import re
from setuptools import setup


version = re.search(
    '^__version__\s*=\s*"(.*)"', open("uploadHAL/version.py").read(), re.M
).group(1)


with open("README.md", "rb") as f:
    long_descr = f.read().decode("utf-8")


setup(
    name="uploadHAL",
    packages=["uploadHAL"],
    scripts=["pdf2hal"],
    version=version,
    description="Python's tools to upload data on HAL.",
    long_description=long_descr,
    author="Luc Laurent",
    author_email="luc.laurent@lecnam.net",
    url="https://github.com/luclaurent/uploadHAL",
    extras_require={"build": ["pdftitle", "pymupdf"]},
)
