import {themes as prismThemes} from 'prism-react-renderer';
import type {Config} from '@docusaurus/types';
import type * as Preset from '@docusaurus/preset-classic';

const config: Config = {
  title: 'Godot Locator',
  tagline: 'Locate Godot scenes, scripts, and resources',
  favicon: 'img/favicon.ico',

  future: {
    v4: true,
  },

  url: 'https://sanitogonzalez.github.io',
  baseUrl: '/godot-locator/',

  organizationName: 'godot-locator',
  projectName: 'godot-locator',

  onBrokenLinks: 'throw',

  i18n: {
    defaultLocale: 'en',
    locales: ['en'],
  },

  presets: [
    [
      'classic',
      {
        docs: false,
        blog: false,
        theme: {
          customCss: './src/css/custom.css',
        },
      } satisfies Preset.Options,
    ],
  ],

  plugins: [
    [
      '@docusaurus/plugin-content-docs',
      {
        id: 'plugin',
        path: '../docs/plugin',
        routeBasePath: 'plugin',
        sidebarPath: './sidebars.ts',
      },
    ],
    [
      '@docusaurus/plugin-content-docs',
      {
        id: 'cli',
        path: '../docs/cli',
        routeBasePath: 'cli',
        sidebarPath: './sidebars.ts',
      },
    ],
    [
      '@docusaurus/plugin-content-docs',
      {
        id: 'mcp',
        path: '../docs/mcp',
        routeBasePath: 'mcp',
        sidebarPath: './sidebars.ts',
      },
    ],
  ],

  themeConfig: {
    image: 'img/docusaurus-social-card.jpg',
    colorMode: {
      respectPrefersColorScheme: true,
    },
    navbar: {
      title: 'Godot Locator',
      logo: {
        alt: 'Godot Locator Logo',
        src: 'img/logo.svg',
      },
      items: [
        {
          type: 'docSidebar',
          sidebarId: 'sidebar',
          docsPluginId: 'plugin',
          position: 'left',
          label: 'Plugin',
        },
        {
          type: 'docSidebar',
          sidebarId: 'sidebar',
          docsPluginId: 'cli',
          position: 'left',
          label: 'CLI',
        },
        {
          type: 'docSidebar',
          sidebarId: 'sidebar',
          docsPluginId: 'mcp',
          position: 'left',
          label: 'MCP',
        },
        {
          href: 'https://github.com/sanitogonzalez/godot-locator',
          position: 'right',
          className: 'header-github-link',
          'aria-label': 'GitHub repository',
        },
      ],
    },
    footer: {
      style: 'dark',
      copyright: `Copyright © ${new Date().getFullYear()} Gangsan Jeong`,
    },
    prism: {
      theme: prismThemes.github,
      darkTheme: prismThemes.dracula,
    },
  } satisfies Preset.ThemeConfig,
};

export default config;
