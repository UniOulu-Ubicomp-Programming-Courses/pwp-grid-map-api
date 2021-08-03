from setuptools import find_packages, setup

setup(
    name="pwp-inventory-service",
    version="0.1.0",
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        "flask",
        "flask-restful",
        "flask-sqlalchemy",
        "flask-caching",
        "flask-accept",
        "jsonschema",
        "SQLAlchemy",
        "python-slugify"
    ]    
)