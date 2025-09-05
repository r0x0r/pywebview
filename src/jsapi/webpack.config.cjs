const path = require('path');
const TerserPlugin = require('terser-webpack-plugin');

const terserOptions = {
  terserOptions: {
    format: {
      comments: false, // Remove all comments
      beautify: true,  // Keep code readable
      indent_level: 2, // Keep indentation
      quote_style: 1,  // Preserve original quotes (1 = preserve, 3 = prefer single)
      quote_keys: true, // Always quote object keys for IE compatibility
      safari10: true   // Fix Safari 10 iterator bug and other IE issues
    },
    compress: {
      properties: false // Don't convert ['foo'] to .foo to avoid reserved word issues
    },
    mangle: false,     // Don't mangle variable names
    ecma: 5           // Target ECMAScript 5 (IE9+)
  },
  extractComments: false // Don't extract comments to separate file
};

module.exports = [
  // Main API bundle with polyfills
  {
    name: 'api',
    entry: './src/main.js',
    target: ['web', 'es5'], // Target ES5 for IE11 compatibility
    output: {
      path: path.resolve(__dirname, '../../webview/js'),
      filename: 'pywebview-api.js',
      clean: false,
      environment: {
        // Force webpack to generate ES5-compatible code
        arrowFunction: false,
        const: false,
        destructuring: false,
        forOf: false
      }
    },
    module: {
      rules: [
        {
          test: /\.js$/,
          exclude: /node_modules/,
          use: {
            loader: 'babel-loader',
            options: {
              presets: [
                ['@babel/preset-env', {
                  targets: {
                    ie: '11'
                  },
                  useBuiltIns: 'usage',
                  corejs: 3
                }]
              ],
              /*
              plugins: [
                // Transform reserved keywords to bracket notation
                function() {
                  return {
                    visitor: {
                      MemberExpression(path) {
                        const property = path.node.property;
                        if (path.node.computed === false &&
                            property.type === 'Identifier' &&
                            property.name === 'return') {
                          path.node.computed = true;
                          property.type = 'StringLiteral';
                          property.value = 'return';
                          delete property.name;
                        }
                      }
                    }
                  };
                }
              ] */
            }
          }
        }
      ]
    },
    optimization: {
      minimize: true,
      minimizer: [new TerserPlugin(terserOptions)]
    },
    resolve: {
      extensions: ['.js']
    },
    devtool: false
  },
  // Finish bundle without polyfills - just transpilation
  {
    name: 'finish',
    entry: './src/finish.js',
    target: ['web', 'es5'], // Target ES5 for IE11 compatibility
    output: {
      path: path.resolve(__dirname, '../../webview/js'),
      filename: 'pywebview-finish.js',
      clean: false,
      environment: {
        // Force webpack to generate ES5-compatible code
        arrowFunction: false,
        const: false,
        destructuring: false,
        forOf: false
      }
    },
    module: {
      rules: [
        {
          test: /\.js$/,
          exclude: /node_modules/,
          use: {
            loader: 'babel-loader',
            options: {
              presets: [
                ['@babel/preset-env', {
                  targets: {
                    ie: '11'
                  },
                  useBuiltIns: false // No polyfills for finish bundle
                }]
              ],
              plugins: [
                // Transform reserved keywords to bracket notation
                function() {
                  return {
                    visitor: {
                      MemberExpression(path) {
                        const property = path.node.property;
                        if (path.node.computed === false &&
                            property.type === 'Identifier' &&
                            property.name === 'return') {
                          path.node.computed = true;
                          property.type = 'StringLiteral';
                          property.value = 'return';
                          delete property.name;
                        }
                      }
                    }
                  };
                }
              ]
            }
          }
        }
      ]
    },
    optimization: {
      minimize: true,
      minimizer: [new TerserPlugin(terserOptions)]
    },
    resolve: {
      extensions: ['.js']
    },
    devtool: false
  }
];
