import os
import pytest


if __name__ == '__main__':
    os.environ['USE_QT'] = ''
    pytest.main()