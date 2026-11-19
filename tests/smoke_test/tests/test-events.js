describe('Window events tests', function() {
    // What the network events cover differs between backends, see NetworkAPI.support()
    let support = {};
    let requestEvent = true;
    let responseEvent = true;

    before(async function() {
        support = await window.pywebview.api.net.support();
        requestEvent = support.request;
        // Android reports responses for https:// requests, such as Mocha loaded from unpkg.com
        const renderer = await window.pywebview.api.eval('webview.renderer');
        responseEvent = support.response || (requestEvent && renderer === 'android-webkit');
    });

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
            ];
            if (requestEvent) expectedEvents.push('request_sent');
            if (responseEvent) expectedEvents.push('response_received');

            // Check that all expected events are present and set to true
            expectedEvents.forEach(eventName => {
                expect(events).to.have.property(eventName);
                expect(events[eventName]).to.be.ok;
            });
        });

        it('should handle request_sent event with data', async function() {
            if (!requestEvent) this.skip();
            // Check if request_sent event contains request data
            const requestSentValue = await window.pywebview.api.eval('events.get("request_sent")');
            expect(requestSentValue).to.not.be.null;
            // The value could be True (boolean) or contain request data
            expect(requestSentValue).to.not.be.undefined;
        });

        it('should handle response_received event with data', async function() {
            if (!responseEvent) this.skip();
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

    describe('Network events', function() {
        const path = (url) => new URL(url).pathname;
        const requested = (log, p) => log.requests.filter(r => path(r.url) === p);
        const lastHit = (log, p) => (log.hits[p] || []).slice(-1)[0];

        it('should report the main document request', async function() {
            if (!support.request) this.skip();
            const log = await window.pywebview.api.net.log();
            const requests = requested(log, '/');
            expect(requests).to.not.be.empty;
            expect(requests[0].method).to.equal('GET');
        });

        it('should report the main document response', async function() {
            if (!support.response) this.skip();
            const response = await window.pywebview.api.net.wait_for_response('/');
            expect(response).to.not.be.null;
            expect(response.status_code).to.equal(200);
        });

        it('should send a header added to the main document request', async function() {
            if (!support.headers) this.skip();
            const log = await window.pywebview.api.net.log();
            expect(lastHit(log, '/')).to.equal('smoke');
        });

        it('should report a fetch request and its response', async function() {
            if (!support.subresource_request && !support.subresource_response) this.skip();
            const result = await (await fetch('/smoke/data')).json();
            expect(result.name).to.equal('data');

            if (support.subresource_response) {
                const response = await window.pywebview.api.net.wait_for_response('/smoke/data');
                expect(response).to.not.be.null;
                expect(response.status_code).to.equal(200);
            }
            if (support.subresource_request) {
                const log = await window.pywebview.api.net.log();
                expect(requested(log, '/smoke/data')).to.not.be.empty;
            }
        });

        it('should send a header added to a fetch request', async function() {
            if (!support.subresource_headers) this.skip();
            await fetch('/smoke/headers');
            const log = await window.pywebview.api.net.log();
            expect(lastHit(log, '/smoke/headers')).to.equal('smoke');
        });

        it('should cancel a fetch request', async function() {
            if (!support.subresource_cancel) this.skip();
            // A cancelled request fails or receives an empty 204 response, depending on the backend
            await fetch('/smoke/blocked').catch(() => null);
            await testUtils.wait(500);
            const log = await window.pywebview.api.net.log();
            expect(requested(log, '/smoke/blocked')).to.not.be.empty;
            expect(log.hits).to.not.have.property('/smoke/blocked');
        });

        it('should cancel a navigation', async function() {
            if (!support.navigation_cancel) this.skip();
            this.timeout(20000);
            expect(await window.pywebview.api.net.cancel_navigation()).to.equal(0);
        });
    });
});
