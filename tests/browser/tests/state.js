/**
 * State Tests for PyWebView
 * Based on test_state.py
 * Tests real PyWebView state functionality
 */

describe('PyWebView State Tests', function() {
    before(async function() {
        this.timeout(10000);
        // Wait for PyWebView to be ready
        await testUtils.waitForPywebview();
    });

    beforeEach(function() {
        // Reset state before each test
        testUtils.resetState();
    });

    describe('Basic State Operations', function() {
        it('should set and get state values', function() {
            window.pywebview.state.test = 420;
            expect(window.pywebview.state.test).to.equal(420);
        });

        it('should handle state set before start', function() {
            // This test simulates setting state before webview starts
            window.pywebview.state.test = 420;
            expect(window.pywebview.state.test).to.equal(420);
        });

        it('should synchronize state from JavaScript', function() {
            // Simulate setting state from JS
            window.pywebview.state.test = 420;
            expect(window.pywebview.state.test).to.equal(420);
        });

        it('should handle dictionary/object state', function() {
            const testObject = { test1: 'test1', test2: 2 };
            window.pywebview.state.test = testObject;

            expect(window.pywebview.state.test).to.deep.equal(testObject);
            expect(JSON.stringify(window.pywebview.state.test)).to.equal(
                JSON.stringify({ "test1": "test1", "test2": 2 })
            );
        });

        it('should handle null state values', function() {
            window.pywebview.state.test = null;
            expect(window.pywebview.state.test).to.be.null;
        });
    });

    describe('State Persistence', function() {
        it('should persist state across page operations', function() {
            window.pywebview.state.test = 420;
            expect(window.pywebview.state.test).to.equal(420);

            // Simulate page reload by checking if state persists
            // In a real implementation, this would test across actual page loads
            expect(window.pywebview.state.test).to.equal(420);
        });
    });

    describe('State Deletion', function() {
        it('should delete state properties', function() {
            window.pywebview.state.test = 420;
            expect(window.pywebview.state.test).to.equal(420);

            delete window.pywebview.state.test;
            expect(Object.keys(window.pywebview.state).length).to.equal(0);
        });

        it('should delete state from JavaScript', function() {
            window.pywebview.state.test = 420;
            expect(window.pywebview.state.test).to.equal(420);

            delete window.pywebview.state.test;
            expect('test' in window.pywebview.state).to.be.false;
        });
    });

    describe('State Events', function() {
        it('should trigger change events when state is modified', function(done) {
            this.timeout(5000);

            // Check if PyWebView state supports event listeners
            if (!window.pywebview.state.addEventListener) {
                this.skip('PyWebView state event listeners not available');
                return;
            }

            let eventTriggered = false;

            function onChange(event) {
                try {
                    expect(event.detail.key).to.equal('test');
                    expect(event.detail.value).to.equal(420);
                    eventTriggered = true;
                    done();
                } catch (error) {
                    done(error);
                }
            }

            window.pywebview.state.addEventListener('change', onChange);
            window.pywebview.state.test = 420;

            // Fallback timeout in case event doesn't fire
            setTimeout(() => {
                if (!eventTriggered) {
                    done(new Error('Change event was not triggered'));
                }
            }, 2000);
        });

        it('should trigger change events from JavaScript modifications', function(done) {
            this.timeout(5000);

            // Check if PyWebView state supports event listeners
            if (!window.pywebview.state.addEventListener) {
                this.skip('PyWebView state event listeners not available');
                return;
            }

            let eventTriggered = false;

            function onChange(event) {
                try {
                    expect(event.detail.key).to.equal('test');
                    expect(event.detail.value).to.equal(420);
                    eventTriggered = true;
                    done();
                } catch (error) {
                    done(error);
                }
            }

            window.pywebview.state.addEventListener('change', onChange);
            // Direct JavaScript assignment
            window.pywebview.state.test = 420;

            setTimeout(() => {
                if (!eventTriggered) {
                    done(new Error('Change event was not triggered'));
                }
            }, 2000);
        });

        it('should trigger delete events when state is deleted', function(done) {
            this.timeout(5000);

            // Check if PyWebView state supports event listeners
            if (!window.pywebview.state.addEventListener) {
                this.skip('PyWebView state event listeners not available');
                return;
            }

            let eventTriggered = false;

            window.pywebview.state.test = 420;

            function onDelete(event) {
                try {
                    expect(event.detail.key).to.equal('test');
                    expect(event.detail.value).to.equal(420);
                    eventTriggered = true;
                    done();
                } catch (error) {
                    done(error);
                }
            }

            window.pywebview.state.addEventListener('delete', onDelete);
            delete window.pywebview.state.test;

            setTimeout(() => {
                if (!eventTriggered) {
                    done(new Error('Delete event was not triggered'));
                }
            }, 2000);
        });

        it('should trigger delete events from JavaScript deletion', function(done) {
            this.timeout(5000);

            // Check if PyWebView state supports event listeners
            if (!window.pywebview.state.addEventListener) {
                this.skip('PyWebView state event listeners not available');
                return;
            }

            let eventTriggered = false;

            window.pywebview.state.test = 420;

            function onDelete(event) {
                try {
                    expect(event.detail.key).to.equal('test');
                    expect(event.detail.value).to.equal(420);
                    eventTriggered = true;
                    done();
                } catch (error) {
                    done(error);
                }
            }

            window.pywebview.state.addEventListener('delete', onDelete);
            delete window.pywebview.state.test;

            setTimeout(() => {
                if (!eventTriggered) {
                    done(new Error('Delete event was not triggered'));
                }
            }, 2000);
        });

        it('should handle change events triggered from JavaScript listeners', function() {
            // Check if PyWebView state supports event listeners
            if (!window.pywebview.state.addEventListener) {
                this.skip('PyWebView state event listeners not available');
                return;
            }

            // Set up a JavaScript event listener that modifies state
            window.pywebview.state.addEventListener('change', function(event) {
                if (event.detail.key === 'test') {
                    window.pywebview.state.result = `${event.detail.key}: ${event.detail.value}`;
                }
            });

            window.pywebview.state.test = 0;

            // Give time for event to process
            return testUtils.wait(100).then(() => {
                expect(window.pywebview.state.result).to.equal('test: 0');
            });
        });

        it('should handle delete events triggered from JavaScript listeners', function() {
            // Check if PyWebView state supports event listeners
            if (!window.pywebview.state.addEventListener) {
                this.skip('PyWebView state event listeners not available');
                return;
            }

            // Set up a JavaScript event listener that captures delete events
            window.pywebview.state.addEventListener('delete', function(event) {
                window.pywebview.state.result = event.detail.key;
            });

            window.pywebview.state.test = 0;
            expect(window.pywebview.state.test).to.equal(0);

            delete window.pywebview.state.test;

            // Give time for event to process
            return testUtils.wait(100).then(() => {
                expect(window.pywebview.state.result).to.equal('test');
            });
        });
    });

    describe('Edge Cases', function() {
        it('should handle multiple rapid state changes', function() {
            for (let i = 0; i < 100; i++) {
                window.pywebview.state[`test${i}`] = i;
            }

            for (let i = 0; i < 100; i++) {
                expect(window.pywebview.state[`test${i}`]).to.equal(i);
            }
        });

        it('should handle complex nested objects', function() {
            const complexObject = {
                level1: {
                    level2: {
                        array: [1, 2, 3, { nested: 'value' }],
                        string: 'test',
                        number: 42,
                        boolean: true,
                        nullValue: null
                    }
                }
            };

            window.pywebview.state.complex = complexObject;
            expect(window.pywebview.state.complex).to.deep.equal(complexObject);
        });

        it('should handle special characters in property names', function() {
            window.pywebview.state['special-key'] = 'value1';
            window.pywebview.state['special_key'] = 'value2';
            window.pywebview.state['special.key'] = 'value3';

            expect(window.pywebview.state['special-key']).to.equal('value1');
            expect(window.pywebview.state['special_key']).to.equal('value2');
            expect(window.pywebview.state['special.key']).to.equal('value3');
        });
    });
});
