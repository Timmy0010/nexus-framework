from setuptools import setup, find_packages

setup(
    name="nexus-framework",
    version="0.1.0",
    description="Nexus Advanced Agent Framework",
    long_description="""
        A flexible, extensible framework for building and managing AI agent systems.
        This framework provides the foundational infrastructure for creating intelligent
        agents that can collaborate, reason, and interact with various tools and data
        sources to automate complex tasks and build next-generation software applications.
    """,
    author="Nexus Framework Team",
    author_email="info@nexusframework.org",
    url="https://github.com/nexusframework/nexus",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.9",
    install_requires=[
        "autogenai>=0.2.0",
        "pydantic>=2.0.0",
        "python-dateutil>=2.8.2",
    ],
)
