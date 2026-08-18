import importlib.util
import os
from pathlib import Path

import setuptools


NAME = 'casperfpga-progska'
DESCRIPTION = 'Optional progska C extension package for casperfpga.'
URL = 'https://github.com/pHantomU94/casperfpga'
AUTHOR = 'Tyrone van Balla & J&J'
EMAIL = 'tvanballa at ska.ac.za'

here = Path(__file__).resolve().parent
repo_root = here.parents[1]

version_module_path = repo_root / '_casperfpga_version.py'
version_spec = importlib.util.spec_from_file_location(
    '_casperfpga_version', version_module_path
)
version_module = importlib.util.module_from_spec(version_spec)
version_spec.loader.exec_module(version_module)
get_build_version = version_module.get_build_version
VERSION = get_build_version()

readme_path = repo_root / 'README.md'
try:
    with readme_path.open(encoding='utf-8') as readme:
        long_description = '\n{}'.format(readme.read())
except Exception:
    long_description = DESCRIPTION

progska_sources = [
    str(repo_root / 'progska' / '_progska.c'),
    str(repo_root / 'progska' / 'progska.c'),
    str(repo_root / 'progska' / 'th.c'),
    str(repo_root / 'progska' / 'netc.c'),
]

setuptools.setup(
    name=NAME,
    version=VERSION,
    description=DESCRIPTION,
    author=AUTHOR,
    author_email=EMAIL,
    url=URL,
    license='GNU GPLv2',
    long_description=long_description,
    long_description_content_type='text/markdown',
    python_requires='>=3.10',
    install_requires=['casperfpga==' + VERSION],
    packages=['casperfpga_progska'],
    package_dir={'casperfpga_progska': 'src/casperfpga_progska'},
    ext_modules=[
        setuptools.Extension(
            'casperfpga_progska.progska',
            sources=progska_sources,
            include_dirs=[str(repo_root / 'progska')],
            language='c',
        )
    ],
    keywords='casper ska meerkat fpga progska',
    classifiers=[
        "License :: OSI Approved :: GNU General Public License v2 (GPLv2)",
        'Programming Language :: Python :: 3.10',
        'Operating System :: POSIX',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Scientific/Engineering :: Astronomy',
    ],
)
