from setuptools import setup, find_packages

setup(
    name="fuzzyterminal",
    version="1.0.0",
    description="Intelligent Terminal with NLP and Remote Execution",
    author="FuzzyTerminal Team",
    packages=find_packages(),
    install_requires=[
        "anthropic",
        "paramiko",
        "pyyaml",
        "rich",
        "prompt_toolkit",
        "asyncssh",
        "openai",
        "google-generativeai",
        "ollama",
    ],
    entry_points={
        "console_scripts": [
            "fuzzy=fuzzyterminal.core:main",
        ],
    },
    python_requires=">=3.8",
)
