import os

from setuptools import find_packages, setup


# Read README.md for long description
def read_readme():
    with open(os.path.join(os.path.dirname(__file__), 'README.md'), encoding='utf-8') as f:
        return f.read()

# Read requirements.txt for install_requires
def read_requirements():
    with open(os.path.join(os.path.dirname(__file__), 'requirements.txt'), encoding='utf-8') as f:
        return [line.strip() for line in f if line.strip() and not line.startswith('#')]

setup(
    name='symbiont-sdk',
    version='0.2.0',
    author='Jascha Wanger / ThirdKey.ai',
    author_email='oss@symbiont.dev',
    description='Python SDK for Symbiont platform with Tool Review and Runtime APIs',
    long_description=read_readme(),
    long_description_content_type='text/markdown',
    url='https://github.com/thirdkeyai/symbiont-sdk-python',
    project_urls={
        'Bug Tracker': 'https://github.com/thirdkeyai/symbiont-sdk-python/issues',
        'Source': 'https://github.com/thirdkeyai/symbiont-sdk-python',
    },
    packages=find_packages(),
    install_requires=read_requirements(),
    python_requires='>=3.7',
    keywords=['symbiont', 'sdk', 'api', 'ai', 'agents'],
    license='MIT',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
    ],
)
