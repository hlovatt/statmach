import setuptools

import statmach


def read_text(file_name: str):
    with open(file_name, "r") as fh:
        return fh.read()


setuptools.setup(
    name='statmach',
    version='1.0.10',
    url=statmach.__repository__,
    license='LIT License',
    # Originally used the text of the license.
    # This doesn't work, see issue #9327, because `license` string can't contain new lines.
    # license=read_text('LICENSE'),
    author=statmach.__author__,
    author_email='howard.lovatt@gmail.com',
    description=statmach.__description__,
    long_description=read_text('README.md'),
    # Alternative long description because read_text('README.md') doesn't work
    # because PyPi can't render README.md - PyPI bug.
    # long_description=f'See {statmach.__repository__} for detailed description.\n',
    long_description_content_type='text/markdown',
    py_modules=['statmach'],
    platforms=['any'],
    classifiers=[
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.5',
)
