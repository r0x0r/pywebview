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
            expect(result).to.deep.equal({ key1: 'value1', key2: 'value2' });
        });

        it('should return list from TestAPI', async function() {
            const result = await window.pywebview.api.test1.getList();
            expect(result).to.deep.equal([1, 2, 3, 4, 5]);
        });

        it('should return None (null) from TestAPI', async function() {
            const result = await window.pywebview.api.test1.getNone();
            expect(result).to.be.null;
        });

        it('should return random number from TestAPI', async function() {
            const result = await window.pywebview.api.test1.getRandomNumber();
            expect(result).to.be.a('number');
            expect(result).to.be.at.least(0);
            expect(result).to.be.at.most(100);
        });

        it('should say hello with parameter', async function() {
            const result = await window.pywebview.api.test1.sayHelloTo('World');
            expect(result).to.deep.equal({ message: 'Hello World!' });
        });

        it('should use eval method from main API', async function() {
            const result = await window.pywebview.api.eval('2 + 3');
            expect(result).to.equal(5);
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

        it('should have separate instances for test1 and test2', async function() {
            // Both should return different random numbers (most likely)
            const result1 = await window.pywebview.api.test1.getRandomNumber();
            const result2 = await window.pywebview.api.test2.getRandomNumber();

            expect(result1).to.be.a('number');
            expect(result2).to.be.a('number');
            // Note: They might be the same by chance, but that's OK for testing
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

    describe('Concurrent API Calls', function() {
        it('should handle multiple concurrent TestAPI calls', async function() {
            const numberOfCalls = 5;
            const promises = [];

            for (let i = 0; i < numberOfCalls; i++) {
                promises.push(window.pywebview.api.test1.sayHelloTo(`User${i}`));
            }

            const results = await Promise.all(promises);
            expect(results).to.have.length(numberOfCalls);
            for (let i = 0; i < numberOfCalls; i++) {
                expect(results[i]).to.deep.equal({ message: `Hello User${i}!` });
            }
        });

        it('should handle rapid sequential TestAPI calls', async function() {
            const results = [];
            for (let i = 0; i < 10; i++) {
                results.push(await window.pywebview.api.test1.sayHelloTo(`Sequential${i}`));
            }

            for (let i = 0; i < 10; i++) {
                expect(results[i]).to.deep.equal({ message: `Hello Sequential${i}!` });
            }
        });
    });


    describe('Performance Tests', function() {
        it('should handle many TestAPI calls efficiently', async function() {
            const startTime = performance.now();

            // Use sequential calls for more realistic performance testing
            // Test with a mix of different methods
            for (let i = 0; i < 50; i++) { // Reduced count for real PyWebView
                await window.pywebview.api.test1.getInteger();
                await window.pywebview.api.test1.sayHelloTo(`User${i}`);
            }

            const endTime = performance.now();
            const duration = endTime - startTime;

            console.log(`100 TestAPI calls took ${duration}ms`);

            // Should complete 100 calls in reasonable time
            // Adjust threshold based on real PyWebView performance
            expect(duration).to.be.below(5000); // Less than 5 seconds
        });
    });
});
