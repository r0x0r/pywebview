import os
import pytest


if __name__ == '__main__':
    os.environ['USE_WIN32'] = ''
    pytest.main()