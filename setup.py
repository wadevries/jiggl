from setuptools import setup

setup(
    name='jiggl',
    version='0.1',
    py_modules=['jiggl'],
    install_requires=[
        'Click',
        'requests',
        'toggl-python-api-client==0.1.0'
    ],
    dependency_links=[
        'git+ssh://git@github.com/wadevries/toggl-python-api-client.git#egg=toggl-python-api-client-0.1.0'
    ],
    entry_points='''
        [console_scripts]
        jiggl=jiggl:run
    '''
)