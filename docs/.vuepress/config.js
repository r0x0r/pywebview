module.exports = {
  title: 'pywebview',
  description: 'Build GUI for your Python program with JavaScript, HTML, and CSS',
  ga: 'UA-12494025-18',
  themeConfig: {
    repo: 'r0x0r/pywebview',
    docsDir: 'docs',
    docsBranch: 'docs',
    editLinks: true,
    editLinkText: 'Help us improve this page!',
    //sidebarDepth: 3,
    nav: [
      { text: 'Guide', link: '/guide/' },
      { text: 'Examples', link: '/examples/' },
      { text: 'Contributing', link: '/contributing/' },
      { text: 'Changelog', link: 'https://github.com/r0x0r/pywebview/blob/master/CHANGELOG.md' },
    ],
    sidebar: {
      '/guide/': [
          {
          title: 'Basics',
          collapsable: false,
          children: [
            '/guide/installation',
            '/guide/usage'
          ]
        },
        {
          title: 'Development',
          collapsable: false,
          children: [
            '/guide/api',
            '/guide/debugging',
            '/guide/freezing',
            '/guide/security',
            '/guide/virtualenv',
            '/guide/renderer',
          ]
        }
      ],
      '/examples/': [
        'change_url',
        'css_load',
        'debug',
        'destroy_window',
        'fullscreen',
        'get_current_url',
        'html_load',
        'js_evaluate',
        'js_api',
        'loading_animation',
        'localization',
        'min_size',
        'multiple_windows',
        'open_file_dialog',
        'open_url',
        'quit_confirm',
        'save_file_dialog',
        'toggle_fullscreen',
        'window_title_change'
      ],

      '/contributing/': [
        'development',
        'bug_reporting',
        'donating',
        'documentation'
      ]
    }
  }
}