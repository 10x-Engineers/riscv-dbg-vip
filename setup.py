"""
Shim setup.py for backward compatibility with setuptools < 64.

Modern pip uses pyproject.toml directly. This file exists only so that
'pip install -e .' works on systems with older setuptools that don't
support PEP 660 editable installs.
"""
from setuptools import setup, find_packages

setup(
    name="pydebug",
    version="0.1.0",
    description="RISC-V Debug Compliance Framework",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    package_data={
        "pydebug": [
            "c_bridge/*.c",
            "c_bridge/*.h",
            "sv/**/*.sv",
            "sv/templates/*.sv",
            "sv/configs/*.json",
            "sv/configs/*.cfg",
        ]
    },
    include_package_data=True,
    python_requires=">=3.8",
    extras_require={
        "test": ["pytest>=7.0"],
    },
    entry_points={
        "console_scripts": [
            "pydebug=pydebug.cli:main",
        ],
    },
)
