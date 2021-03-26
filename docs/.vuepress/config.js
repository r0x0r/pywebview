module.exports = {
  title: 'pywebview',
  description: 'Build GUI for your Python program with JavaScript, HTML, and CSS',
  ga: 'UA-12494025-18',
  plugins: {
    '@vuepress/medium-zoom': {
      selector: 'img.zoom',
      options: {
        margin: 16
      }
    }
  },
  themeConfig: {
    repo: 'r0x0r/pywebview',
    docsDir: 'docs',
    docsBranch: 'docs',
    editLinks: true,
    editLinkText: 'Help us improve this page!',
    logo: '/logo-no-text.png',
    nav: [
      { text: 'Guide', link: '/guide/' },
      { text: 'Examples', link: '/examples/' },
      { text: 'Contributing', link: '/contributing/' },
      { text: 'Blog', link: '/blog/' },
      { text: 'Changelog', link: '/CHANGELOG.md' },
      { text: '2.x', link: 'https://pywebview.flowrl.com/2.4' },
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
            '/guide/architecture',
            '/guide/debugging',
            '/guide/interdomain',
            '/guide/freezing',
            '/guide/security',
            '/guide/virtualenv',
            '/guide/renderer',
          ]
        }
      ],
      '/examples/': [
        'cef',
        'change_url',
        'css_load',
        'close_confirm',
        'debug',
        'destroy_window',
        'events',
        'frameless',
        'fullscreen',
        'get_elements',
        'get_current_url',
        'hide_window',
        'html_load',
        'js_evaluate',
        'js_api',
        'loading_animation',
        'links',
        'localization',
        'min_size',
        'minimize_window',
        'move_window',
        'multiple_windows',
        'open_file_dialog',
        'open_url',
        'resize_window',
        'save_file_dialog',
        'screens',
        'toggle_fullscreen',
        'user_agent',
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