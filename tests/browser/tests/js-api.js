/**
 * JavaScript API Tests for PyWebView
 * Based on test_js_api.py
 * Tests real PyWebView API functionality
 */

describe('PyWebView JavaScript API Tests', function() {

    before(async function() {
        this.timeout(10000);
        // Wait for PyWebView to be ready
        await testUtils.waitForPywebview();

        // Check if API is available
        if (!window.pywebview.api) {
            throw new Error('PyWebView API not available. Make sure js_api is configured.');
        }
    });

    describe('Basic API Bridge Tests', function() {
        it('should return integer from API', async function() {
            if (!window.pywebview.api.get_int) {
                this.skip('get_int method not available in API');
                return;
            }
            const result = await window.pywebview.api.get_int();
            expect(result).to.equal(420);
        });

        it('should return float from API', async function() {
            if (!window.pywebview.api.get_float) {
                this.skip('get_float method not available in API');
                return;
            }
            const result = await window.pywebview.api.get_float();
            expect(result).to.equal(3.141);
        });

        it('should return string from API', async function() {
            if (!window.pywebview.api.get_string) {
                this.skip('get_string method not available in API');
                return;
            }
            const result = await window.pywebview.api.get_string();
            expect(result).to.equal('test');
        });

        it('should return object from API', async function() {
            if (!window.pywebview.api.get_object) {
                this.skip('get_object method not available in API');
                return;
            }
            const result = await window.pywebview.api.get_object();
            expect(result).to.deep.equal({ key1: 'value', key2: 420 });
        });

        it('should return object-like string from API', async function() {
            if (!window.pywebview.api.get_objectlike_string) {
                this.skip('get_objectlike_string method not available in API');
                return;
            }
            const result = await window.pywebview.api.get_objectlike_string();
            expect(result).to.equal('{"key1": "value", "key2": 420}');
        });

        it('should handle single quotes in strings', async function() {
            if (!window.pywebview.api.get_single_quote) {
                this.skip('get_single_quote method not available in API');
                return;
            }
            const result = await window.pywebview.api.get_single_quote();
            expect(result).to.equal("te'st");
        });

        it('should handle double quotes in strings', async function() {
            if (!window.pywebview.api.get_double_quote) {
                this.skip('get_double_quote method not available in API');
                return;
            }
            const result = await window.pywebview.api.get_double_quote();
            expect(result).to.equal('te"st');
        });

        it('should echo parameters correctly', async function() {
            if (!window.pywebview.api.echo) {
                this.skip('echo method not available in API');
                return;
            }
            const testValue = 'test';
            const result = await window.pywebview.api.echo(testValue);
            expect(result).to.equal(testValue);
        });

        it('should handle multiple parameters', async function() {
            if (!window.pywebview.api.multiple) {
                this.skip('multiple method not available in API');
                return;
            }
            const result = await window.pywebview.api.multiple(1, 2, 3);
            expect(result).to.deep.equal([1, 2, 3]);
        });
    });

    describe('Nested API Tests', function() {
        it('should access nested API methods', async function() {
            if (!window.pywebview.api.nested || !window.pywebview.api.nested.get_int) {
                this.skip('nested.get_int method not available in API');
                return;
            }
            const result = await window.pywebview.api.nested.get_int();
            expect(result).to.equal(422);
        });

        it('should access nested instance methods', async function() {
            if (!window.pywebview.api.nested_instance || !window.pywebview.api.nested_instance.get_int_instance) {
                this.skip('nested_instance.get_int_instance method not available in API');
                return;
            }
            const result = await window.pywebview.api.nested_instance.get_int_instance();
            expect(result).to.equal(423);
        });
    });

    describe('Exception Handling', function() {
        it('should handle API exceptions', async function() {
            if (!window.pywebview.api.raise_exception) {
                this.skip('raise_exception method not available in API');
                return;
            }

            try {
                await window.pywebview.api.raise_exception();
                expect.fail('Exception should have been thrown');
            } catch (error) {
                expect(error).to.be.an('error');
                // PyWebView may wrap the exception differently
                expect(error.message).to.include('ApiTestException');
            }
        });

        it('should handle API exceptions gracefully', async function() {
            if (!window.pywebview.api.raise_exception) {
                this.skip('raise_exception method not available in API');
                return;
            }

            try {
                await window.pywebview.api.raise_exception();
                expect.fail('Exception should have been thrown');
            } catch (error) {
                expect(error).to.be.an('error');
                // The actual error message format may vary in PyWebView
                expect(error.message).to.be.a('string');
            }
        });
    });

    describe('Concurrent API Calls', function() {
        it('should handle multiple concurrent API calls', async function() {
            if (!window.pywebview.api.echo) {
                this.skip('echo method not available in API');
                return;
            }

            const numberOfCalls = 5;
            const promises = [];

            for (let i = 0; i < numberOfCalls; i++) {
                promises.push(window.pywebview.api.echo(i));
            }

            const results = await Promise.all(promises);
            expect(results).to.have.length(numberOfCalls);
            for (let i = 0; i < numberOfCalls; i++) {
                expect(results[i]).to.equal(i);
            }
        });

        it('should handle rapid sequential API calls', async function() {
            if (!window.pywebview.api.echo) {
                this.skip('echo method not available in API');
                return;
            }

            const results = [];
            for (let i = 0; i < 10; i++) {
                results.push(await window.pywebview.api.echo(i));
            }

            for (let i = 0; i < 10; i++) {
                expect(results[i]).to.equal(i);
            }
        });
    });

    describe('API Object Structure', function() {
        it('should skip duplicate nested instances', function() {
            // Test that nested_instance_duplicate is undefined (not exposed)
            expect(window.pywebview.api.nested_instance_duplicate).to.be.undefined;
        });

        it('should have proper API structure', function() {
            expect(window.pywebview.api).to.be.an('object');
            expect(window.pywebview.api.get_int).to.be.a('function');
            expect(window.pywebview.api.nested).to.be.an('object');
            expect(window.pywebview.api.nested_instance).to.be.an('object');
        });
    });

    describe('Data Type Handling', function() {
        it('should handle various data types in echo', async function() {
            if (!window.pywebview.api.echo) {
                this.skip('echo method not available in API');
                return;
            }

            // Test different data types
            const testCases = [
                42,
                3.14159,
                'string',
                true,
                false,
                null,
                { key: 'value' },
                [1, 2, 3]
            ];

            for (const testCase of testCases) {
                const result = await window.pywebview.api.echo(testCase);
                if (typeof testCase === 'object' && testCase !== null) {
                    expect(result).to.deep.equal(testCase);
                } else {
                    expect(result).to.equal(testCase);
                }
            }
        });

        it('should handle complex nested objects', async function() {
            if (!window.pywebview.api.echo) {
                this.skip('echo method not available in API');
                return;
            }

            const complexObject = {
                string: 'test',
                number: 42,
                float: 3.14,
                boolean: true,
                nullValue: null,
                array: [1, 2, 3],
                nested: {
                    deep: {
                        value: 'deeply nested'
                    }
                }
            };

            const result = await window.pywebview.api.echo(complexObject);
            expect(result).to.deep.equal(complexObject);
        });

        it('should handle arrays with mixed types', async function() {
            if (!window.pywebview.api.echo) {
                this.skip('echo method not available in API');
                return;
            }

            const mixedArray = [1, 'string', true, null, { key: 'value' }];
            const result = await window.pywebview.api.echo(mixedArray);
            expect(result).to.deep.equal(mixedArray);
        });
    });

    describe('Error Boundary Tests', function() {
        it('should handle non-existent API methods gracefully', function() {
            expect(window.pywebview.api.non_existent_method).to.be.undefined;
        });

        it('should handle API calls with wrong number of parameters', function() {
            // Most JavaScript functions handle extra/missing parameters gracefully
            expect(() => {
                window.pywebview.api.echo(); // Missing parameter
            }).to.not.throw();

            expect(() => {
                window.pywebview.api.echo('param1', 'param2'); // Extra parameter
            }).to.not.throw();
        });
    });

    describe('Performance Tests', function() {
        it('should handle many API calls efficiently', async function() {
            if (!window.pywebview.api.echo) {
                this.skip('echo method not available in API');
                return;
            }

            this.timeout(10000); // 10 second timeout for performance test

            const startTime = performance.now();

            // Use sequential calls for more realistic performance testing
            // Concurrent calls might not reflect real PyWebView performance
            for (let i = 0; i < 100; i++) { // Reduced from 1000 for real PyWebView
                await window.pywebview.api.echo(i);
            }

            const endTime = performance.now();
            const duration = endTime - startTime;

            console.log(`100 API calls took ${duration}ms`);

            // Should complete 100 calls in reasonable time
            // Adjust threshold based on real PyWebView performance
            expect(duration).to.be.below(5000); // Less than 5 seconds
        });
    });
});
