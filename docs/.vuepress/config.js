const dirTree = require('directory-tree');
const path = require('path');
const { generateExamples } = require('./generate-examples');

generateExamples(path.join(__dirname, '../../examples'), path.join(__dirname, '../examples'));

const examples = dirTree(path.join(__dirname, '../examples'), { extensions: /\.md/ });

module.exports = {
  title: 'pywebview',
  description: 'Build GUI for your Python program with JavaScript, HTML, and CSS',
  locales: {
    '/': {
      lang: 'en-US',
      title: 'pywebview',
      description: 'Build GUI for your Python program with JavaScript, HTML, and CSS',
    },
    '/zh/': {
      lang: 'zh-CN',
      title: 'pywebview',
      description: '使用 JavaScript、HTML 和 CSS 为 Python 程序构建 GUI',
    }
  },
  port: 8082,
  themeConfig: {
    repo: 'r0x0r/pywebview',
    docsDir: 'docs',
    docsBranch: 'docs',
    editLinks: true,
    editLinkText: 'Help us improve this page!',
    logo: '/logo-no-text.png',
    locales: {
      "/": {
        label: 'English',
        nav: [
          { text: 'Guide', link: '/guide/' },
          { text: 'Examples', link: '/examples/' },
          { text: 'Contributing', link: '/contributing/' },
          { text: 'Blog', link: '/blog/' },
          { text: 'Changelog', link: '/CHANGELOG.md' },
          { text: '2.x', link: 'https://pywebview.flowrl.com/2.4' },
          { text: '3.x', link: 'https://pywebview.flowrl.com/3.7' },
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
                '/guide/dom',
                '/guide/faq',
                '/guide/interdomain',
                '/guide/freezing',
                '/guide/security',
                '/guide/web_engine',
              ]
            }
          ],
          '/examples/': examples.children
            .filter(file => path.parse(file.name).name !== 'README')
            .map(file => path.parse(file.name).name),

          '/contributing/': [
            'development',
            'bug_reporting',
            'donating',
            'documentation'
          ]
        }
      },
      "/zh/": {
        label: '中文',
        selectText: '选择语言',
        nav: [
          { text: '入门', link: '/zh/guide/' },
          { text: '示例', link: '/examples/' },
          { text: '贡献', link: '/zh/contributing/' },
          { text: '博客', link: '/zh/blog/' },
          { text: '更新日志', link: '/zh/CHANGELOG.md' },
          { text: '2.x(英文)', link: 'https://pywebview.flowrl.com/2.4' },
          { text: '3.x(英文)', link: 'https://pywebview.flowrl.com/3.7' },
        ],
        sidebar: {
          '/zh/guide/': [
            {
              title: '基础',
              collapsable: false,
              children: [
                '/zh/guide/installation',
                '/zh/guide/usage'
              ]
            },
            {
              title: '开发',
              collapsable: false,
              children: [
                '/zh/guide/api',
                '/zh/guide/architecture',
                '/zh/guide/debugging',
                '/zh/guide/dom',
                '/zh/guide/faq',
                '/zh/guide/interdomain',
                '/zh/guide/freezing',
                '/zh/guide/security',
                '/zh/guide/web_engine',
              ]
            }
          ],
          '/zh/examples/': examples.children
            .filter(file => path.parse(file.name).name !== 'README')
            .map(file => path.parse(file.name).name),

          '/zh/contributing/': [
            'development',
            'bug_reporting',
            'donating',
            'documentation'
          ]
        }
      }
    },
    displayAllHeaders: true,

  }
}

