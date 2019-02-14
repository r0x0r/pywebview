import os
import pytest


if __name__ == '__main__':
    os.environ['PYWEBVIEW_GUI'] = 'win32'
    pytest.main()