from setuptools import setup, find_packages

setup(
    name="spellcaster",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "numpy",
        "torch",
        "matplotlib",
        "tqdm",
        "pygame"
    ],
) 