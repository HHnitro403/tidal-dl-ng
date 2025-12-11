"""Setup script for TIDAL Playlist Monitor."""

from setuptools import setup, find_packages
from pathlib import Path

# Read requirements
requirements_path = Path(__file__).parent / 'requirements.txt'
with open(requirements_path, 'r', encoding='utf-8') as f:
    requirements = [
        line.strip() for line in f
        if line.strip() and not line.startswith('#')
    ]

# Read README
readme_path = Path(__file__).parent / 'README.md'
with open(readme_path, 'r', encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='tidal-playlist-monitor',
    version='0.1.0',
    description='Background service that monitors TIDAL playlists and auto-downloads new tracks',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='TIDAL DL NG Community',
    python_requires='>=3.12',
    packages=find_packages(),
    install_requires=requirements,
    entry_points={
        'console_scripts': [
            'tidal-playlist-monitor=tidal_playlist_monitor.cli:app',
            'tidal-monitor=tidal_playlist_monitor.cli:app',
        ],
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: End Users/Desktop',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: 3.13',
    ],
)
