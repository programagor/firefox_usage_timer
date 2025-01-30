from setuptools import setup, find_packages

setup(
    name='firefox-usage-timer',
    version='0.1.0',
    packages=find_packages(),
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'firefox-usage-timer = firefox_usage_timer.main:main'
        ]
    },
    # If you have e.g. a license file, you can declare it here, or in MANIFEST.in
    description='A PyQt application that tracks Firefox usage time',
    author='Jiří Bednář',
    author_email='jbednar@isocta.com',
    url='https://github.com/programagor/firefox_usage_timer',
    install_requires=[
        'PyQt6',
    ],
)