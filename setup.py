from setuptools import setup, find_packages

setup(
    name="codereview-local",
    version="0.1.1",
    description="Local RAG-based code review CLI. No API keys. Runs fully on your machine.",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Muhammad",
    url="https://github.com/Muhammad-NSQ/codereview",
    packages=find_packages(),
    install_requires=[
        "typer",
        "chromadb",
        "sentence-transformers",
        "tree-sitter",
        "tree-sitter-python",
        "requests",
        "torch",
    ],
    entry_points={
        "console_scripts": [
            "codereview=codereview.cli:app",
        ],
    },
    python_requires=">=3.10",
    license="MIT",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Quality Assurance",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
)
