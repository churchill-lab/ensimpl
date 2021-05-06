#!/usr/bin/env python
# -*- coding: utf-8 -*-
from glob import glob
import os
from setuptools import setup, find_packages

with open('README.md') as readme_file:
    readme = readme_file.read()

with open('HISTORY.md') as history_file:
    history = history_file.read()

requirements = []
test_requirements = []


on_rtd = os.environ.get('READTHEDOCS', None)

if not on_rtd:
    requirements.append('Flask==1.1.1')
    requirements.append('Flask-Cors==3.0.9')
    requirements.append('Flask-Compress==1.4.0')
    requirements.append('gunicorn==19.9.0')
    requirements.append('PyMySQL==0.9.3')
    requirements.append('natsort==6.0.0')
    requirements.append('tabulate==0.8.5')

setup(
    name='ensimpl',
    version='0.1.0',
    description="Ensembl tools",
    long_description=readme + '\n\n' + history,
    author="Matthew Vincent",
    author_email='matt.vincent@jax.org',
    url='https://github.com/churchill-lab/ensimpl',
    packages=find_packages(),
    entry_points='''
            [console_scripts]
            ensimpl=ensimpl.cli.cli:cli
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
        'Programming Language :: Python :: 3.7',
    ]
    #test_suite='tests',
    #tests_require=test_requirements
)
