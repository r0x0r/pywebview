from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs
from PyInstaller.compat import is_win

datas = []
if is_win:
    datas = collect_data_files('webview', subdir='lib')
    binaries = collect_dynamic_libs('webview')


datas += collect_data_files('webview', subdir='js')