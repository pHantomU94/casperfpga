import glob
import importlib.util
import os

import setuptools

NAME = 'casperfpga'
DESCRIPTION = 'Talk to CASPER hardware devices using katcp or dcp. See https://github.com/casper-astro/casperfpga for more.'
URL = 'https://github.com/casper-astro/casperfpga'
TFTPY_FORK_URL = 'https://github.com/pHantomU94/tftpy/archive/refs/heads/fix/upload-filelike-cleanup.zip'

AUTHOR  = 'Tyrone van Balla & J&J'
EMAIL   = 'tvanballa at ska.ac.za'
here = os.path.abspath(os.path.dirname(__file__))

version_module_path = os.path.join(here, '_casperfpga_version.py')
version_spec = importlib.util.spec_from_file_location('_casperfpga_version', version_module_path)
version_module = importlib.util.module_from_spec(version_spec)
version_spec.loader.exec_module(version_module)
get_build_version = version_module.get_build_version
VERSION = get_build_version()

try:
    with open(os.path.join(here, 'README.md')) as readme:
        # long_description = readme.read().split('\n')[2]
        long_description = '\n{}'.format(readme.read())
except Exception as exc:
    # Probably didn't find the file?
    long_description = DESCRIPTION


data_files = ['tengbe_mmap.txt', 'tengbe_mmap_legacy.txt', 'fortygbe_mmap_legacy.txt']


def should_build_progska():
    env_value = os.environ.get('CASPERFPGA_BUILD_PROGSKA')
    if env_value is not None:
        return env_value.lower() not in ('0', 'false', 'no')
    return False


def get_ext_modules():
    if not should_build_progska():
        return []
    return [
        setuptools.Extension(
            'casperfpga.progska',
            sources=[
                'progska/_progska.c',
                'progska/progska.c',
                'progska/th.c',
                'progska/netc.c',
            ],
            include_dirs=['progska'],
            language='c',
        )
    ]

setuptools.setup(
    name=NAME,
    version=VERSION,
    description=DESCRIPTION,
    author=AUTHOR,
    author_email=EMAIL,
    url=URL,
    download_url='https://pypi.org/project/casperfpga',
    license='GNU GPLv2',
    long_description=long_description,
    long_description_content_type='text/markdown',
    # Specify version in-line here
    install_requires=[
        'IPython',
        'future',
        'numpy',
        'katcp>=0.9.3',
        'odict',
        'setuptools',
        'tornado',
        'redis',
        'tftpy @ ' + TFTPY_FORK_URL,
        'progressbar2',
        'requests',
        'circus',
        'crcmod'
    ],
    extras_require = {'test': ['pytest', 'pytest-cov', 'pytest-datadir']},
    packages=['casperfpga', 'casperfpga.debug'],
    py_modules=['_casperfpga_version'],
    package_dir={'casperfpga': 'src', 'casperfpga.debug': 'debug'},
    package_data={'casperfpga': data_files},
    scripts=glob.glob('scripts/*'),
    ext_modules=get_ext_modules(),
    python_requires='>=3.8',
    # Required for PyPI
    keywords='casper ska meerkat fpga',
    classifiers=[
        "License :: OSI Approved :: GNU General Public License v2 (GPLv2)",
        'Programming Language :: Python :: 3.8',
        'Operating System :: OS Independent',
	    'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Scientific/Engineering :: Astronomy',
    ]
)

# end
