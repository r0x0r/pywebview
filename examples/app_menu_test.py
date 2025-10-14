"""
Application Menu Example (macOS)

This example demonstrates how to add custom menu items to the main application menu
(the first menu in the menu bar that shows the app name).

On macOS, custom items are placed between "About" and "Services" menu items,
surrounded by separators. On other platforms, menus with title 'app' are ignored.

Usage:
    python app_menu_test.py

The app menu will contain:
    - About <App Name>
    - ─────────────────
    - Preferences...          (custom)
    - ─────────────────
    - Check for Updates       (custom)
    - License Information     (custom)
    - ─────────────────
    - Services
    - Hide/Show All/Quit
"""

import webview
from webview.menu import Menu, MenuAction, MenuSeparator


def open_preferences():
    """Open preferences window (example action)."""
    active_window = webview.active_window()
    if active_window:
        active_window.load_html(
            '<h1>⚙️ Preferences</h1>'
            '<p>This would open your application preferences.</p>'
            '<p>Typically triggered by ⌘,</p>'
        )


def check_for_updates():
    """Check for application updates (example action)."""
    active_window = webview.active_window()
    if active_window:
        active_window.load_html(
            '<h1>🔄 Check for Updates</h1>'
            '<p>Checking for updates...</p>'
            '<p>You are using the latest version!</p>'
        )


def show_license():
    """Show license information (example action)."""
    active_window = webview.active_window()
    if active_window:
        active_window.load_html(
            '<h1>📄 License</h1>'
            '<p><strong>BSD 3-Clause License</strong></p>'
            '<p>Copyright (c) 2025, Your Application</p>'
        )


def file_action():
    """Regular menu action (for comparison)."""
    active_window = webview.active_window()
    if active_window:
        active_window.load_html(
            '<h1>📁 File Menu Action</h1>'
            '<p>This is a regular menu item from the File menu.</p>'
        )


if __name__ == '__main__':
    # Define app menu items using the special '__app__' title
    # These items will be added to the main application menu on macOS
    app_menu = Menu('__app__', [
        MenuAction('Preferences...', open_preferences),
        MenuSeparator(),  # Visual separator between items
        MenuAction('Check for Updates', check_for_updates),
        MenuAction('License Information', show_license)
    ])

    # Regular menus work as before
    file_menu = Menu('File', [
        MenuAction('Test Action', file_action)
    ])

    # Create window with both app menu and regular menus
    window = webview.create_window(
        'App Menu Example',
        html='''
            <style>
                body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                       padding: 40px; line-height: 1.6; }
                h1 { color: #333; }
                .info { background: #f0f0f0; padding: 15px; border-radius: 8px; margin: 20px 0; }
                code { background: #e8e8e8; padding: 2px 6px; border-radius: 3px; }
            </style>
            <h1>🍎 App Menu Example</h1>
            <div class="info">
                <p><strong>macOS Only:</strong> Check the application menu (first menu in menu bar)
                for custom items!</p>
                <p>You should see:</p>
                <ul>
                    <li><strong>Preferences...</strong></li>
                    <li><strong>Check for Updates</strong></li>
                    <li><strong>License Information</strong></li>
                </ul>
                <p>These items appear between "About" and "Services".</p>
            </div>
            <div class="info">
                <p><strong>How it works:</strong></p>
                <p>Use <code>Menu('__app__', [...])</code> to add items to the app menu.</p>
                <p>On other platforms, '__app__' menus are automatically ignored.</p>
            </div>
        ''',
        menu=[app_menu, file_menu]
    )

    webview.start()
