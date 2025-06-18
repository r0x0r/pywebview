
describe('State Tests', function() {
    before(async function() {
        await testUtils.waitForPywebview();
    });

    beforeEach(function() {
        // Reset state before each test
        testUtils.resetState();
    });

    describe('Basic State Operations', function() {
        it('should set and get state values', async function() {
            window.pywebview.state.test = 420;
            expect(await window.pywebview.api.eval('window.state.test')).to.equal(420);
        });

        it('should access predefined state from Python', async function() {
            // Test predefined state values from runner.py create_state function
            expect(await window.pywebview.api.eval('window.state.number')).to.equal(0);
            expect(await window.pywebview.api.eval('window.state.message')).to.equal('test');
        });

        it('should handle dictionary/object state', async function() {
            const testObject = { test1: 'test1', test2: 2 };
            window.pywebview.state.test = testObject;

            expect(window.pywebview.state.test).to.deep.equal(testObject);
            expect(JSON.stringify(await window.pywebview.api.eval('window.state.test'))).to.equal(
                JSON.stringify(testObject)
            );
        });

        it('should access predefined dictionary state from Python', async function() {
            // Test predefined dict state from runner.py
            const dictResult = await window.pywebview.api.eval('window.state.dict');
            expect(dictResult).to.deep.equal({ key: 'value' });
        });

        it('should access predefined list state from Python', async function() {
            // Test predefined list state from runner.py
            const listResult = await window.pywebview.api.eval('window.state.list');
            expect(listResult).to.deep.equal([1, 2, 3]);
        });

        it('should access predefined nested state from Python', async function() {
            // Test predefined nested state from runner.py
            const nestedResult = await window.pywebview.api.eval('window.state.nested');
            expect(nestedResult).to.deep.equal({
                'a': 1,
                'b': [1, 2, 3],
                'c': {'d': 4}
            });
        });

        it('should handle null state values', async function() {
            window.pywebview.state.test = null;
            expect(window.pywebview.state.test).to.be.null;
            expect(await window.pywebview.api.eval('window.state.test')).to.be.null;
        });
    });


    describe('State Deletion', function() {
        it('should delete state properties', async function() {
            window.pywebview.state.test = 420;
            expect(await window.pywebview.api.eval('window.state.test')).to.equal(420);

            delete window.pywebview.state.test;
            expect(await window.pywebview.api.eval('hasattr(window.state, "test")')).to.be.false;
        });

        it('should delete state from JavaScript', async function() {
            window.pywebview.state.test = 420;
            expect(await window.pywebview.api.eval('window.state.test')).to.equal(420);

            delete window.pywebview.state.test;
            expect('test' in window.pywebview.state).to.be.false;
            expect(await window.pywebview.api.eval('hasattr(window.state, "test")')).to.be.false;
        });

        it('should not delete predefined state accidentally', async function() {
            // Ensure predefined state remains accessible after operations
            window.pywebview.state.temp = 'temporary';
            delete window.pywebview.state.temp;

            // Predefined state should still be there
            expect(await window.pywebview.api.eval('window.state.number')).to.equal(0);
            expect(await window.pywebview.api.eval('window.state.message')).to.equal('test');
        });
    });

    describe('State Events', function() {
        let eventListeners = [];

        afterEach(function() {
            // Remove all event listeners added during tests
            eventListeners.forEach(({ type, listener }) => {
                window.pywebview.state.removeEventListener(type, listener);
            });
            eventListeners = [];
        });

        it('should trigger change events when state is modified', function(done) {
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
            eventListeners.push({ type: 'change', listener: onChange });
            window.pywebview.state.test = 420;

            // Fallback timeout in case event doesn't fire
            setTimeout(() => {
                if (!eventTriggered) {
                    done(new Error('Change event was not triggered'));
                }
            }, 10000);
        });

        it('should trigger change events for predefined state modifications', function(done) {
            let eventTriggered = false;

            function onChange(event) {
                try {
                    expect(event.detail.key).to.equal('number');
                    expect(event.detail.value).to.equal(100);
                    eventTriggered = true;
                    done();
                } catch (error) {
                    done(error);
                }
            }

            window.pywebview.state.addEventListener('change', onChange);
            eventListeners.push({ type: 'change', listener: onChange });
            // Modify predefined state
            window.pywebview.state.number = 100;

            setTimeout(() => {
                if (!eventTriggered) {
                    done(new Error('Change event was not triggered for predefined state'));
                }
            }, 2000);
        });

        it('should trigger change events from JavaScript modifications', function(done) {
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
            eventListeners.push({ type: 'change', listener: onChange });
            // Direct JavaScript assignment
            window.pywebview.state.test = 420;

            setTimeout(() => {
                if (!eventTriggered) {
                    done(new Error('Change event was not triggered'));
                }
            }, 2000);
        });

        it('should trigger delete events when state is deleted', function(done) {
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
            eventListeners.push({ type: 'delete', listener: onDelete });
            delete window.pywebview.state.test;

            setTimeout(() => {
                if (!eventTriggered) {
                    done(new Error('Delete event was not triggered'));
                }
            }, 2000);
        });

        it('should trigger delete events from JavaScript deletion', function(done) {

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
            eventListeners.push({ type: 'delete', listener: onDelete });
            delete window.pywebview.state.test;

            setTimeout(() => {
                if (!eventTriggered) {
                    done(new Error('Delete event was not triggered'));
                }
            }, 2000);
        });

        it('should handle change events triggered from JavaScript listeners', async function() {
            // Set up a JavaScript event listener that modifies state
            function changeHandler(event) {
                if (event.detail.key === 'test') {
                    window.pywebview.state.result = `${event.detail.key}: ${event.detail.value}`;
                }
            }

            window.pywebview.state.addEventListener('change', changeHandler);
            eventListeners.push({ type: 'change', listener: changeHandler });

            window.pywebview.state.test = 0;

            await testUtils.wait(100);
            expect(await window.pywebview.api.eval('window.state.result')).to.equal('test: 0');
        });

        it('should handle delete events triggered from JavaScript listeners', async function() {
            // Set up a JavaScript event listener that captures delete events
            function deleteHandler(event) {
                window.pywebview.state.result = event.detail.key;
            }

            window.pywebview.state.addEventListener('delete', deleteHandler);
            eventListeners.push({ type: 'delete', listener: deleteHandler });

            window.pywebview.state.test = 0;
            expect(await window.pywebview.api.eval('window.state.test')).to.equal(0);

            delete window.pywebview.state.test;

            // Give time for event to process
            await testUtils.wait(100);
            expect(await window.pywebview.api.eval('window.state.result')).to.equal('test');
        });
    });

    describe('Edge Cases', function() {
        it('should handle multiple rapid state changes', async function() {
            for (let i = 0; i < 100; i++) {
                window.pywebview.state[`test${i}`] = i;
            }

            for (let i = 0; i < 100; i++) {
                expect(await window.pywebview.api.eval(`window.state.test${i}`)).to.equal(i);
            }
        });

        it('should handle complex nested objects', async function() {
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

            const evalResult = await window.pywebview.api.eval('window.state.complex');
            expect(evalResult).to.deep.equal(complexObject);
        });

        it('should handle special characters in property names', async function() {
            window.pywebview.state['special-key'] = 'value1';
            window.pywebview.state['special_key'] = 'value2';
            window.pywebview.state['special.key'] = 'value3';

            expect(await window.pywebview.api.eval('getattr(window.state, "special-key")')).to.equal('value1');
            expect(await window.pywebview.api.eval('getattr(window.state, "special_key")')).to.equal('value2');
            expect(await window.pywebview.api.eval('getattr(window.state, "special.key")')).to.equal('value3');
        });
    });
});
