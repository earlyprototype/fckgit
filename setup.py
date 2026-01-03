from setuptools import setup

setup(
    name="fckgit",
    version="0.1.0",
    description="Auto-commit with AI-generated messages using Gemini",
    author="Fab2",
    py_modules=["fckgit"],
    install_requires=[
        "google-generativeai>=0.3.0",
    ],
    entry_points={
        "console_scripts": [
            "fckgit=fckgit:main",
        ],
    },
    python_requires=">=3.8",
)
