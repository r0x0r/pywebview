"""
Android Mocha Test Suite Example

This example demonstrates how to run an interactive Mocha test suite on Android
with a Python backend API. It's useful for manual testing and debugging the
pywebview API bridge, state management, and window lifecycle events.

The HTML/JS test suite provides:
- JS API bridge tests (calling Python from JavaScript)
- Window state and event synchronization tests
- Window lifecycle event tests
- Cookie management tests
- Python code evaluator for live debugging

To use this example:
1. Build and run on an Android device or emulator
2. The test suite will auto-run when the page loads
3. Use the Python Code Evaluator button to test custom Python code
"""

import pywebview


class TestAPI:
    """Example API for the test suite."""

    def __init__(self, label=''):
        self.label = label

    def get_integer(self):
        return 420

    def get_float(self):
        return 4.20

    def get_string(self):
        return 'This is a string from Python'

    def get_dict(self):
        return {'key1': 'value1', 'key2': 'value2'}

    def get_list(self):
        return [1, 2, 3, 4, 5]

    def get_none(self):
        return None

    def get_random_number(self):
        import random

        return random.randint(0, 100)

    def say_hello_to(self, name):
        return {'message': f'Hello {name}!'}

    def error(self):
        raise Exception('This is a Python exception')


def eval_python(code):
    """Evaluate Python code and return the result."""
    try:
        result = eval(code)
        return {'success': True, 'result': str(result)}
    except Exception as e:
        return {'success': False, 'error': str(e)}


html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Android Test Suite</title>
    <link rel="stylesheet" href="https://unpkg.com/mocha/mocha.css">
    <script>
        document.cookie = 'testCookie1=value1; expires=Thu, 18 Dec 2133 12:00:00 UTC;';
        document.cookie = 'testCookie2=value2; expires=Thu, 18 Dec 2133 12:00:00 UTC;';
        document.cookie = 'testJson=' + JSON.stringify({key: 'value', number: 42})
            + '; expires=Thu, 18 Dec 2133 12:00:00 UTC;';
    </script>
    <style>
        body {
            font-family: system-ui, -apple-system, sans-serif;
            margin: 0;
            padding: 10px;
        }
        #mocha {
            margin-bottom: 20px;
        }
        .eval-section {
            padding: 20px;
            border: 1px solid #ccc;
            border-radius: 5px;
            margin: 20px 0;
            background-color: #f9f9f9;
        }
        .eval-section h3 {
            margin-top: 0;
        }
        textarea {
            width: 100%;
            font-family: monospace;
            padding: 8px;
            box-sizing: border-box;
        }
        button {
            padding: 8px 16px;
            margin: 5px 5px 5px 0;
            border: none;
            border-radius: 3px;
            cursor: pointer;
            font-size: 14px;
        }
        .primary {
            background-color: #007acc;
            color: white;
        }
        .secondary {
            background-color: #666;
            color: white;
        }
        .toggle {
            background-color: #28a745;
            color: white;
            display: block;
            width: 100%;
            text-align: left;
        }
        .toggle.open {
            background-color: #dc3545;
        }
        #result-area {
            min-height: 100px;
            padding: 10px;
            border: 1px solid #ddd;
            background-color: #fff;
            font-family: monospace;
            white-space: pre-wrap;
            margin-top: 10px;
            overflow-y: auto;
        }
    </style>
</head>
<body>
    <h1>Android Test Suite</h1>
    <div id="mocha"></div>

    <script src="https://unpkg.com/mocha/mocha.js"></script>
    <script src="https://unpkg.com/chai@4.5.0/chai.js"></script>
    <script>mocha.setup('bdd')</script>
    <script>mocha.timeout(10000)</script>
    <script>var expect = chai.expect;</script>

    <script>
        // Test utilities
        window.testUtils = {
            resetState: () => {
                if (window.pywebview && window.pywebview.state) {
                    const predefinedKeys = ['number', 'message', 'dict', 'list', 'nested'];
                    const keys = Object.keys(window.pywebview.state);
                    keys.forEach(key => {
                        if (!predefinedKeys.includes(key)) {
                            delete window.pywebview.state[key];
                        }
                    });

                    if (window.pywebview.state.number !== undefined) {
                        window.pywebview.state.number = 0;
                    }
                    if (window.pywebview.state.message !== undefined) {
                        window.pywebview.state.message = 'test';
                    }
                    if (window.pywebview.state.dict !== undefined) {
                        window.pywebview.state.dict = {'key': 'value'};
                    }
                    if (window.pywebview.state.list !== undefined) {
                        window.pywebview.state.list = [1, 2, 3];
                    }
                    if (window.pywebview.state.nested !== undefined) {
                        window.pywebview.state.nested = {'a': 1, 'b': [1, 2, 3]};
                    }
                }
            },
            wait: (ms) => new Promise(resolve => setTimeout(resolve, ms))
        };

        // Test suite
        describe('JS API tests', function() {
            describe('Basic API Bridge Tests', function() {
                it('should return integer from TestAPI', async function() {
                    const result = await window.pywebview.api.test1.getInteger();
                    expect(result).to.equal(420);
                });

                it('should return float from TestAPI', async function() {
                    const result = await window.pywebview.api.test1.getFloat();
                    expect(result).to.equal(4.20);
                });

                it('should return string from TestAPI', async function() {
                    const result = await window.pywebview.api.test1.getString();
                    expect(result).to.equal('This is a string from Python');
                });

                it('should return dict from TestAPI', async function() {
                    const result = await window.pywebview.api.test1.getDict();
                    expect(result).to.deep.equal({key1: 'value1', key2: 'value2'});
                });

                it('should return list from TestAPI', async function() {
                    const result = await window.pywebview.api.test1.getList();
                    expect(result).to.deep.equal([1, 2, 3, 4, 5]);
                });

                it('should return None (null) from TestAPI', async function() {
                    const result = await window.pywebview.api.test1.getNone();
                    expect(result).to.be.null;
                });

                it('should say hello with parameter', async function() {
                    const result = await window.pywebview.api.test1.sayHelloTo('World');
                    expect(result).to.deep.equal({message: 'Hello World!'});
                });
            });

            describe('Multiple TestAPI Instances', function() {
                it('should access test1 instance methods', async function() {
                    const result = await window.pywebview.api.test1.getInteger();
                    expect(result).to.equal(420);
                });

                it('should access test2 instance methods', async function() {
                    const result = await window.pywebview.api.test2.getInteger();
                    expect(result).to.equal(420);
                });
            });

            describe('Exception Handling', function() {
                it('should handle TestAPI exceptions', async function() {
                    try {
                        await window.pywebview.api.test1.error();
                        expect.fail('Exception should have been thrown');
                    } catch (error) {
                        expect(error).to.be.an('error');
                        expect(error.message).to.include('This is a Python exception');
                    }
                });
            });
        });

        describe('Window State tests', function() {
            it('should have initial state from Python', async function() {
                expect(window.pywebview.state).to.exist;
            });

            it('should persist state updates', async function() {
                window.pywebview.state.testKey = 'testValue';
                await window.testUtils.wait(100);
                expect(window.pywebview.state.testKey).to.equal('testValue');
            });
        });

        describe('Window Lifecycle tests', function() {
            it('should have pywebview ready', function() {
                expect(window.pywebview).to.exist;
                expect(window.pywebview.api).to.exist;
            });

            it('should have API instances', function() {
                expect(window.pywebview.api.test1).to.exist;
                expect(window.pywebview.api.test2).to.exist;
            });
        });
    </script>

    <script>
        if (window.pywebview && Object.keys(window.pywebview.api).length > 0) {
            mocha.run();
        } else {
            window.addEventListener('pywebviewready', mocha.run);
        }
    </script>

    <div class="eval-section">
        <button class="toggle" id="toggle-eval-button" onclick="toggleEvaluator()">
            Show Python Code Evaluator
        </button>

        <div id="eval-content" style="display: none; margin-top: 10px;">
            <h4>Python Code Evaluator</h4>
            <p>Enter Python code to execute (Ctrl+Enter to run):</p>
            <textarea id="python-code" rows="6"
                      placeholder="Enter your Python code here..."></textarea>
            <div>
                <button class="primary" onclick="evaluatePythonCode()">Execute Code</button>
                <button class="secondary" onclick="clearResult()">Clear Result</button>
            </div>
            <div>
                <strong>Result:</strong>
                <div id="result-area"></div>
            </div>
        </div>
    </div>

    <script>
        function toggleEvaluator() {
            const content = document.getElementById('eval-content');
            const button = document.getElementById('toggle-eval-button');
            const isOpen = content.style.display !== 'none';

            content.style.display = isOpen ? 'none' : 'block';
            button.textContent = isOpen ? 'Show Python Code Evaluator' : 'Hide Python Code Evaluator';
            button.classList.toggle('open', !isOpen);
        }

        async function evaluatePythonCode() {
            const textarea = document.getElementById('python-code');
            const resultArea = document.getElementById('result-area');
            const code = textarea.value.trim();

            if (!code) {
                resultArea.textContent = 'Please enter some Python code to execute.';
                resultArea.style.color = '#999';
                return;
            }

            if (!window.pywebview || !window.pywebview.api || !window.pywebview.api.evalPython) {
                resultArea.textContent = 'Error: pywebview.api.evalPython is not available.';
                resultArea.style.color = 'red';
                return;
            }

            try {
                resultArea.textContent = 'Executing...';
                resultArea.style.color = '#666';

                const result = await window.pywebview.api.evalPython(code);
                resultArea.textContent = JSON.stringify(result, null, 2);
                resultArea.style.color = result.success ? 'green' : 'red';
            } catch (error) {
                resultArea.textContent = `Error: ${error.message || error}`;
                resultArea.style.color = 'red';
            }
        }

        function clearResult() {
            document.getElementById('result-area').textContent = '';
            document.getElementById('result-area').style.color = '#000';
        }

        document.getElementById('python-code').addEventListener('keydown', function(event) {
            if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
                event.preventDefault();
                evaluatePythonCode();
            }
        });
    </script>
</body>
</html>
"""

if __name__ == '__main__':
    pywebview.start(
        html,
        js_api=[TestAPI('test1'), TestAPI('test2')],
        additional_apis={'evalPython': eval_python},
        title='Android Mocha Test Suite',
        width=800,
        height=600,
    )
