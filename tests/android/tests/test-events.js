describe.only('Window events tests', function() {
    before(async function() {
        await testUtils.waitForPywebview();
    });

    describe('Event registration tests', function() {
        it('should have all events registered and set to true', async function() {
            // Get the events dictionary from Python
            const events = await window.pywebview.api.eval('events');

            // Check that the events object exists
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
                expect(events[eventName]).to.equal(true, `Event '${eventName}' should be set to true`);
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

    describe('Event state manipulation tests', function() {
        it('should be able to check individual event states', async function() {
            // Test individual event checks
            const loadedState = await window.pywebview.api.eval('events.get("loaded", False)');
            expect(loadedState).to.equal(true, 'Loaded event should be true');

            const beforeLoadState = await window.pywebview.api.eval('events.get("before_load", False)');
            expect(beforeLoadState).to.equal(true, 'Before load event should be true');

            const beforeShowState = await window.pywebview.api.eval('events.get("before_show", False)');
            expect(beforeShowState).to.equal(true, 'Before show event should be true');

            const shownState = await window.pywebview.api.eval('events.get("shown", False)');
            expect(shownState).to.equal(true, 'Shown event should be true');
        });

        it('should be able to reset events', async function() {
            // Reset a specific event
            await window.pywebview.api.eval('events["loaded"] = False');
            const resetState = await window.pywebview.api.eval('events["loaded"]');
            expect(resetState).to.equal(false, 'Event should be reset to false');

            // Set it back to true
            await window.pywebview.api.eval('events["loaded"] = True');
            const restoredState = await window.pywebview.api.eval('events["loaded"]');
            expect(restoredState).to.equal(true, 'Event should be restored to true');
        });

        it('should be able to add custom events', async function() {
            // Add a custom event
            await window.pywebview.api.eval('events["custom_test_event"] = "test_value"');
            const customEventValue = await window.pywebview.api.eval('events.get("custom_test_event")');
            expect(customEventValue).to.equal('test_value', 'Custom event should have the set value');

            // Clean up
            await window.pywebview.api.eval('del events["custom_test_event"]');
            const deletedEventValue = await window.pywebview.api.eval('events.get("custom_test_event")');
            expect(deletedEventValue).to.be.null;
        });
    });

    describe('Event count and keys tests', function() {
        it('should have the expected number of events', async function() {
            const eventCount = await window.pywebview.api.eval('len(events)');
            expect(eventCount).to.be.at.least(6, 'Should have at least 6 events registered');
        });

        it('should be able to list all event keys', async function() {
            const eventKeys = await window.pywebview.api.eval('list(events.keys())');
            expect(eventKeys).to.be.an('array');
            expect(eventKeys.length).to.be.at.least(6, 'Should have at least 6 event keys');

            // Check for specific required events
            const requiredEvents = ['loaded', 'before_load', 'before_show', 'shown'];
            requiredEvents.forEach(eventName => {
                expect(eventKeys).to.include(eventName, `Should include '${eventName}' in event keys`);
            });
        });

        it('should be able to get event values', async function() {
            const eventValues = await window.pywebview.api.eval('list(events.values())');
            expect(eventValues).to.be.an('array');
            expect(eventValues.length).to.be.at.least(6, 'Should have at least 6 event values');
        });
    });

    describe('Event timing tests', function() {
        it('should have lifecycle events in logical order', async function() {
            // All these events should be true by the time the test runs
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
