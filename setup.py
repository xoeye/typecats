"""Setup for typecats"""
# type: ignore
from setuptools import find_packages, setup  # type: ignore

PKG_NAME = "typecats"
about = {}  # type: ignore
exec(open(f"{PKG_NAME}/__about__.py").read(), about)  # pylint: disable=exec-used

with open("README.md") as fh:
    long_description = fh.read()

setup(
    name=PKG_NAME,
    version=about["__version__"],
    author=about["__author__"],
    author_email=about["__author_email__"],
    url="https://github.com/xoeye/typecats",
    description="Structure unstructured data for the purpose of static type checking",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    package_data={"": ["py.typed"]},
    python_requires=">=3.7",
    install_requires=[
        "attrs == 21.4.0",
        "cattrs == 22.1.0",
        "typing_extensions >= 3.7",
    ],
    # it is important to keep these install_requires basically in sync with the Pipfile as well.
)
