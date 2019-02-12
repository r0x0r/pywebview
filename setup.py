import os
import platform
from setuptools import setup

extras_require = {
    'qt': ['PyQt5'],
    'cef': ['cefpython3'],
}

install_requires = [
    'pythonnet ; sys_platform == "win32"',
    'pyobjc ; sys_platform == "darwin"',
    'PyQt5 ; sys_platform == "openbsd6"',
]


with open("README.md") as fh:
    long_description = fh.read()

setup(
    name="pywebview",
    author="Roman Sirokov",
    author_email="roman@flowrl.com",
    description=("Build GUI for your Python program with JavaScript, HTML, and CSS."),
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/r0x0r/pywebview",
    download_url="https://github.com/r0x0r/pywebview/archive/2.2.1.tar.gz",
    keywords=["gui", "webkit", "html", "web"],
    install_requires=install_requires,
    extras_require=extras_require,
    version="2.2.1",
    include_package_data=True,
    packages=["webview", "webview.js"],
    package_data={"webview": ['webview/lib/WebBrowserInterop.x64.dll', 'webview/lib/WebBrowserInterop.x86.dll']},
    license="New BSD license",
    classifiers=[
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Environment :: MacOS X",
        "Environment :: Win32 (MS Windows)",
        "Environment :: X11 Applications :: GTK",
        "Environment :: X11 Applications :: Qt",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Software Development :: User Interfaces"
    ],
)
