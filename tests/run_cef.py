import os

import pytest

if __name__ == '__main__':
    os.environ['PYWEBVIEW2_GUI'] = 'cef'
    pytest.main()
