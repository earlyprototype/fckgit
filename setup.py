from setuptools import setup, find_packages

setup(
    name="fckgit",
    version="0.2.0",
    description="Auto-commit with AI-generated messages using Gemini - Now with Silicon Valley Mode!",
    author="early_prototype",
    py_modules=["fckgit"],
    packages=find_packages(),
    install_requires=[
        "google-genai>=1.0.0",
        "python-dotenv>=0.19.0",
        "watchdog>=2.0.0",
    ],
    extras_require={
        "mcp": ["mcp>=1.0.0", "psutil>=5.9.0"],
    },
    entry_points={
        "console_scripts": [
            "fckgit=fckgit:main",
        ],
    },
    python_requires=">=3.8",
)
