from setuptools import setup, find_packages
import os
import sys

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="vayuapi",
    version="0.1.5",
    author="VayuAPI Team",
    author_email="codeswithalok@gmail.com",
    description="The fastest Python async API framework for rapid development with AI/ML support",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/vayuapi/vayuapi",
    project_urls={
        "Documentation": "https://vayuapi.amrits.in/",
        "Source Code": "https://github.com/vayuapi/vayuapi",
        "Bug Tracker": "https://github.com/vayuapi/vayuapi/issues",
        "Changelog": "https://github.com/vayuapi/vayuapi/blob/main/CHANGELOG.md",
    },
    packages=find_packages(exclude=["tests", "tests.*", "examples", "examples.*"]),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Information Technology",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Operating System :: POSIX",
        "Operating System :: POSIX :: Linux",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: MacOS",
        "Operating System :: Unix",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Programming Language :: Python :: 3.14",
        "Framework :: AsyncIO",
        "Framework :: Pydantic :: 2",
        "Topic :: Internet",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: HTTP Servers",
        "Topic :: Software Development",
        "Topic :: Software Development :: Libraries",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Typing :: Typed",
    ],
    python_requires=">=3.11,<3.16",
    install_requires=[
        "starlette>=0.35.0,<1.0.0",
        "uvicorn[standard]>=0.27.0,<1.0.0",
        "pydantic>=2.5.0,<3.0.0",
        "uvloop>=0.19.0; sys_platform != 'win32'",  # uvloop not on Windows
        "python-multipart>=0.0.6",
        "jinja2>=3.1.2",
        "httpx>=0.26.0",
        "itsdangerous",
        "pydantic",
        "pydantic[email]"
    ],
    include_package_data=True,
    package_data={
        "vayuapi": ["py.typed", "admin/templates/*"],
    },
    zip_safe=False,
    extras_require={
        # Django ORM support
        "django": [
            "django>=4.2.0,<6.0.0",
            "psycopg2-binary>=2.9.0; sys_platform != 'win32'",
            "psycopg2>=2.9.0; sys_platform == 'win32'",
        ],
        # Async ORM support
        "orm": [
            "tortoise-orm>=0.20.0,<1.0.0",
            "asyncpg>=0.29.0",
            "aiomysql>=0.2.0",
        ],
        # SQLAlchemy async
        "sqlalchemy": [
            "sqlalchemy[asyncio]>=2.0.0,<3.0.0",
            "asyncpg>=0.29.0",
        ],
        # NoSQL databases
        "nosql": [
            "motor>=3.3.0",
            "redis>=5.0.0",
        ],
        # Vector databases
        "vector": [
            "chromadb>=0.4.0",
        ],
        # AI/ML integrations
        "ai": [
            "langchain>=0.1.0",
            "langchain-openai>=0.0.5",
            "langchain-community>=0.0.20",
            "openai>=1.10.0",
        ],
        # Task scheduling
        "scheduler": [
            "apscheduler>=3.10.0",
        ],
        # Security
        "security": [
            "cryptography>=41.0.0",
            "pyjwt>=2.8.0",
            "passlib[bcrypt]>=1.7.4",
        ],
        # Testing
        "test": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.23.0",
            "pytest-cov>=4.1.0",
            "pytest-timeout>=2.2.0",
            "httpx>=0.26.0",
        ],
        # Development (testing + linting only)
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.23.0",
            "pytest-cov>=4.1.0",
            "pytest-timeout>=2.2.0",
            "black>=24.0.0",
            "ruff>=0.2.0",
            "mypy>=1.8.0",
            "pre-commit>=3.6.0",
        ],
        # Development with all features
        "dev-all": [
            "vayuapi[all]",
            "pytest>=7.4.0",
            "pytest-asyncio>=0.23.0",
            "pytest-cov>=4.1.0",
            "pytest-timeout>=2.2.0",
            "black>=24.0.0",
            "ruff>=0.2.0",
            "mypy>=1.8.0",
            "pre-commit>=3.6.0",
        ],
        # All features
        "all": [
            "django>=4.2.0,<6.0.0",
            "tortoise-orm>=0.20.0",
            "motor>=3.3.0",
            "redis>=5.0.0",
            "chromadb>=0.4.0",
            "langchain>=0.1.0",
            "cryptography>=41.0.0",
            "apscheduler>=3.10.0",
        ],
    },
    keywords=[
        "api", "async", "asyncio", "framework", "fastapi", "starlette",
        "django", "orm", "rest", "restful", "websocket", "microservices",
        "ai", "ml", "langchain", "rag", "pydantic","pydanticAI","admin", "security"
    ],
)
