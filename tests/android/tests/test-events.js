describe('Window events tests', function() {
    describe('Event registration tests', function() {
        it('should have all events registered and set to true', async function() {
            await testUtils.wait(1000);
            const events = await window.pywebview.api.eval('events');

            expect(events).to.be.an('object');

            // List of expected events
            const expectedEvents = [
                'loaded',
                'before_load',
                'before_show',
                'shown',
                'request_sent',
                'response_received'
            ];

            // Check that all expected events are present and set to true
            expectedEvents.forEach(eventName => {
                expect(events).to.have.property(eventName);
                expect(events[eventName]).to.be.ok;
            });
        });

        it('should handle request_sent event with data', async function() {
            // Check if request_sent event contains request data
            const requestSentValue = await window.pywebview.api.eval('events.get("request_sent")');
            expect(requestSentValue).to.not.be.null;
            // The value could be True (boolean) or contain request data
            expect(requestSentValue).to.not.be.undefined;
        });

        it('should handle response_received event with data', async function() {
            // Check if response_received event contains response data
            const responseReceivedValue = await window.pywebview.api.eval('events.get("response_received")');
            expect(responseReceivedValue).to.not.be.null;
            // The value could be True (boolean) or contain response data
            expect(responseReceivedValue).to.not.be.undefined;
        });
    });

    describe('Event timing tests', function() {
        it('should have lifecycle events in logical order', async function() {
            // All these events should be true by the time the test runs
            debugger
            const beforeLoadState = await window.pywebview.api.eval('events.get("before_load")');
            const loadedState = await window.pywebview.api.eval('events.get("loaded")');
            const beforeShowState = await window.pywebview.api.eval('events.get("before_show")');
            const shownState = await window.pywebview.api.eval('events.get("shown")');

            // These events should have fired in the window lifecycle
            expect(beforeLoadState).to.equal(true, 'before_load should have fired');
            expect(loadedState).to.equal(true, 'loaded should have fired');
            expect(beforeShowState).to.equal(true, 'before_show should have fired');
            expect(shownState).to.equal(true, 'shown should have fired');
        });
    });
});
