import codecs
import os

from setuptools import find_packages, setup

here = os.path.abspath(os.path.dirname(__file__))

with codecs.open(os.path.join(here, "README.rst"), encoding="utf-8") as f:
    long_description = f.read()


setup(
    name="trustlines-relay",
    setup_requires=["setuptools_scm"],
    use_scm_version=True,
    description="Relay Server for the Trustlines Network",
    long_description=long_description,
    # The project's main homepage.
    url="https://github.com/trustlines-protocol/relay",
    # Author details
    author="Trustlines-Network",
    author_email="contact@brainbot.com",
    license="MIT",
    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        "Development Status :: 2 - Pre-Alpha",
        # Indicate who your project is intended for
        "Intended Audience :: Developers",
        # Pick your license as you wish (should match "license" above)
        "License :: OSI Approved :: MIT License",
        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
    ],
    # What does your project relate to?
    keywords="trustlines",
    packages=find_packages("src"),
    package_dir={"": "src"},
    install_requires=[
        "flask",
        "flask_restful",
        "flask_cors",
        "sentry-sdk[flask]",
        "webargs",
        "gevent",
        "web3>=4.7.1",
        "networkx>=2.0",
        "trustlines-contracts-bin>=1.1.0,<1.2.0",
        "trustlines-contracts-deploy>=1.1.0,<1.2.0",
        "sqlalchemy",
        "eth-utils",
        "tinyrpc",
        "gevent-websocket",
        "marshmallow>=3.0.0b7",
        "marshmallow-oneofschema>=2.0.0",
        "flask-sockets",
        "firebase-admin",
        "psycopg2",
        "psycogreen",
        "wrapt",
        "attrs",
        "click",
        "toml",
        "cachetools",
    ],
    python_requires=">=3.6",
    entry_points={"console_scripts": ["tl-relay=relay.boot:main"]},
)
