from datetime import datetime
from version import __version__
from setuptools import setup, find_packages

with open("README.md", "r") as fh:
    long_description = fh.read()

with open("version.py", "r") as fh:
    version_number = fh.read()
    start = version_number.find('"')
    end = version_number[start + 1 :].find('"')
    version_number_str = str(version_number[start + 1 : start + end + 1])
    version_number_str = version_number_str.replace("\n", "")

print(">>>" + version_number_str + "<<<")

###############################################################################

setup(
    name="nemesis",
    version=version_number_str,
    author="LIG",
    author_email="ericcccc_z@outlook.com",
    description="A Finance Derivatives Valuation Library",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Mxyzptlk-Z/NEMESIS",
    keywords=["FINANCE", "OPTIONS", "BONDS", "VALUATION", "DERIVATIVES"],
    install_requires=[
        "numpy",
        "numba",
        "scipy",
        "llvmlite",
        "ipython",
        "matplotlib",
        "pandas",
        "prettytable",
        "openpyxl",
        "QuantLib",
    ],
    include_package_date=True,
    packages=find_packages(),
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
)
