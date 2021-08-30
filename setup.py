#!/usr/bin/env python
# -*- coding: utf-8 -*-
from glob import glob
import os
from setuptools import setup, find_packages

with open('README.md') as readme_file:
    readme = readme_file.read()

requirements = []
test_requirements = []


on_rtd = os.environ.get('READTHEDOCS', None)

if not on_rtd:
    with open('requirements.txt') as requirements_file:
        requirements_lines = requirements_file.readlines()
        for line in requirements_lines:
            requirements.append(line)

setup(
    name='ensimpl',
    version='1.0.0',
    description="Ensembl tools",
    long_description=readme,
    author="Matthew Vincent",
    author_email='matt.vincent@jax.org',
    url='https://github.com/churchill-lab/ensimpl',
    packages=find_packages(),
    entry_points='''
            [console_scripts]
            ensimpl=ensimpl.cli:main
        ''',
    #package_dir={'ensimpl':
    #             'ensimpl'},
    include_package_data=True,
    #scripts=glob("bin/*"),
    #setup_requires=requirements,
    install_requires=requirements,
    license="Apache Software License 2.0",
    zip_safe=False,
    keywords='ensimpl',
    classifiers=[
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3.9',
    ]
    #test_suite='tests',
    #tests_require=test_requirements
)
