<template>
  <div class="wrapper">
    <div class="container">
      <div class="highlights-grid">
        <div v-for="highlight in highlights[0].highlights" :key="highlight.title" class="highlight-item">
          <span class="material-symbols-outlined icon">
            {{ highlight.icon }}
          </span>
          <div>
            <h2>{{ highlight.title }}</h2>
            <p>{{ highlight.details }}</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      highlights: [
        {
          header: "Features",
          description: "pywebview is a lightweight BSD-licensed cross-platform wrapper around a webview component. pywebview allows to display HTML content in its own native GUI window. It gives you power of web technologies in your desktop application, hiding the fact that GUI is browser based. pywebview ships with a built-in HTTP server, DOM support in Python and window management functionality.",
          highlights: [
            {
              title: "Cross-platform",
              details: "Compatible with Windows, macOS, Linux, and Android, ensuring a consistent user experience across all major operating systems.",
              icon: "devices"
            },
            {
              title: "Two-way Javascript↔Python communication",
              details: "Facilitate direct communication between Javascript and Python without the need for HTTP or REST.",
              icon: "sync"
            },
            {
              title: "Built-in HTTP server",
              details: "Easily serve static files with the integrated HTTP server, simplifying the process of hosting and accessing your web content.",
              icon: "cloud"
            },
            {
              title: "Window management",
              details: "Control the appearance and behavior of the window, including its size, position, and title. Manage multiple windows with ease.",
              icon: "grid_view"
            },
            {
              title: "Native components",
              details: "Utilize native GUI elements such as menus, message boxes, and file dialogs to provide a seamless user interface.",
              icon: "widgets"
            },
            {
              title: "DOM support",
              details: "Leverage the Python API to manipulate and traverse DOM nodes without resorting to Javascript.",
              icon: "code"
            },
            {
              title: "Enhanced filesystem support",
              details: "Access the full path of dropped files, create save file and open file dialogs on demand.",
              icon: "folder"
            },
            {
              title: "Bundler friendly",
              details: "Easily integrate with popular bundlers like pyinstaller, nuitka, and py2app, streamlining the packaging and distribution of your applications.",
              icon: "package"
            },
            {
              title: "CLI toolchain",
              details: "Scaffold, develop, and package apps into native installers (.msi, .dmg, .deb, .apk) with a single pywebview command-line tool.",
              icon: "terminal"
            },
            {
              title: "Native notifications",
              details: "Show native OS notifications on macOS, Windows, and Linux with a single webview.notify() call.",
              icon: "notifications"
            },
            {
              title: "Secure credential storage",
              details: "Store secrets in the OS-native keychain -- macOS Keychain, Windows DPAPI, or Linux Secret Service -- via webview.keyring.",
              icon: "key"
            },
            {
              title: "Settings persistence",
              details: "Persist app settings to a simple JSON-backed key-value store with webview.store, no extra dependency required.",
              icon: "save"
            },
            {
              title: "System tray icons",
              details: "Add a native tray or menu bar icon with a context menu built from the same Menu API used for your window.",
              icon: "apps"
            },
            {
              title: "Global keyboard shortcuts",
              details: "Register hotkeys that fire even when no pywebview window is focused, with webview.shortcuts.",
              icon: "keyboard"
            },
            {
              title: "Single-instance enforcement",
              details: "Detect an already-running instance of your app and forward the new launch's arguments to it instead of opening a duplicate window.",
              icon: "verified"
            }
          ]
        }
      ]
    };
  }
};
</script>

<style scoped>
.wrapper {
  margin: 3rem 0;
  padding-top: 3rem;
  background: #fbfbfb;
  background-repeat: repeat;
  position: relative;
  width: 100vw;
  margin-right: 0;
  left: 50%;
  right: 50%;
  transform: translateX(-50%);
  overflow: visible;

  [data-theme="dark"] & {
    background: #242429;
  }
}

h2 {
  font-size: 18px;
  border: 0;
}

.container {
  display: flex;
  justify-content: center;
  margin: 0 auto;
  max-width: 80rem;
}

.icon {
  font-size: 50px;
  margin-top: 14px;
  color: #84c99e;
}

.highlights-grid {
  display: grid;
  grid-template-columns: repeat(2, 0.7fr);
  justify-content: center;
  column-gap: 6rem;
  row-gap: 2rem;

  padding: 0 2rem;
  @media (max-width: 600px) {
    grid-template-columns: 1fr;
    padding: 0 1rem;
  }
}

.highlight-item {
  padding: 0 16px ;
  border-radius: 8px;
  min-width: 100px;
  display: flex;
  gap: 1rem;
}
</style>
