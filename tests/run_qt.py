import os
import pytest


if __name__ == '__main__':
    os.environ['PYWEBVIEW_GUI'] = 'qt'
    pytest.main()