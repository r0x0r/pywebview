import { defineUserConfig } from 'vuepress';
import { hopeTheme } from 'vuepress-theme-hope';
import { viteBundler } from '@vuepress/bundler-vite'
import { linksCheckPlugin } from '@vuepress/plugin-links-check'
//import { mediumZoomPlugin } from '@vuepress/plugin-medium-zoom';
import { path } from '@vuepress/utils';
import { generateExamples } from './generate-examples';
import dirTree from 'directory-tree';

generateExamples(path.resolve(__dirname, '../../examples'), path.resolve(__dirname, '../examples'));
const examples = dirTree(path.resolve(__dirname, '../examples'), { extensions: /\.md/ });

export default defineUserConfig({
  title: 'pywebview',
  description: 'Build GUI for your Python program with JavaScript, HTML, and CSS',
  port: 8082,
  bundler: viteBundler({
    viteOptions: {},
    vuePluginOptions: {},
  }),
  head: [
    ['link', { rel: 'stylesheet', href: 'https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@24,400,0,0&icon_names=cloud,code,devices,folder,grid_view,package,sync,widgets' }],
  ],
  theme: hopeTheme({
    repo: 'r0x0r/pywebview',
    docsDir: 'docs',
    docsBranch: 'docs',
    editLinks: true,
    editLinkText: 'Help us improve this page!',
    logo: '/logo-no-text.png',
    markdown: {
      align: true,
      linksCheck: true
    },
    navbar: [
      { text: 'Guide', link: '/guide/' },
      { text: 'API', link: '/api/' },
      { text: 'Examples', link: '/examples/' },
      { text: 'Contributing', link: '/contributing/' },
      { text: 'Blog', link: '/blog/' },
      { text: 'Changelog', link: '/CHANGELOG.md' },
      { text: '2.x', link: 'https://pywebview.flowrl.com/2.4' },
      { text: '3.x', link: 'https://pywebview.flowrl.com/3.7' },
    ],
    displayAllHeaders: true,
    sidebar: {
      '/guide/': [
        {
          text: 'Basics',
          collapsible: false,
          children: [
            '/guide/installation',
            '/guide/usage'
          ]
        },
        {
          text: 'Development',
          collapsible: false,
          children: [
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
    },
    contributors: false
  }),
  plugins: [
    linksCheckPlugin({
      exclude: [
        '/CHANGELOG'
      ],
    })
    // mediumZoomPlugin({
    //   selector: 'img.zoom',
    //   options: {
    //     margin: 16
    //   }
    // })
  ]
});
