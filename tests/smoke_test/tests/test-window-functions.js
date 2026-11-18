// Window functions driven from Python through api.win (see WindowAPI in main.py). Most of them
// are not supported on Android, so desktop-only suites are skipped there.
describe('Window function tests', function() {
    let info;

    before(async function() {
        info = await window.pywebview.api.win.info();
    });

    function desktopOnly() {
        before(function() {
            if (testUtils.isAndroid(info)) this.skip();
        });
    }

    describe('Core', function() {
        it('exposes the renderer and the same token in Python and Javascript', function() {
            expect(info.renderer).to.be.a('string').that.is.not.empty;
            expect(info.token).to.equal(window.pywebview.token);
        });

        it('serves the page from the local HTTP server', async function() {
            const url = await window.pywebview.api.win.get_current_url();
            expect(url).to.match(/^https?:\/\/(127\.0\.0\.1|localhost)/);
            const response = await fetch('index.js');
            expect(response.ok).to.be.true;
        });

        it('calls a function registered with window.expose', async function() {
            expect(await window.pywebview.api.exposed_function('ok')).to.equal('exposed ok');
        });

        it('calls an async Python function', async function() {
            expect(await window.pywebview.api.asyncSleep(50)).to.equal(50);
        });

        it('load_css applies a stylesheet', async function() {
            await window.pywebview.api.win.load_css();
            await testUtils.wait(200);
            const value = getComputedStyle(document.documentElement)
                .getPropertyValue('--pywebview-css-probe').trim();
            expect(value).to.equal('42');
        });

        it('evaluate_js resolves promises to a callback', async function() {
            expect(await window.pywebview.api.win.evaluate_js_promise()).to.equal(42);
        });

        it('evaluate_js raises JavascriptException', async function() {
            const message = await window.pywebview.api.win.evaluate_js_exception();
            expect(message).to.include('smoke test error');
        });

        it('state set from Python is visible in Javascript', async function() {
            const value = await window.pywebview.api.win.python_state('fromPython', {a: [1, 2]});
            expect(value).to.deep.equal({a: [1, 2]});
            expect(window.pywebview.state.fromPython).to.deep.equal({a: [1, 2]});
        });
    });

    describe('Window manipulation', function() {
        desktopOnly();

        it('lists at least one screen', function() {
            expect(info.screens).to.be.at.least(1);
        });

        it('sets the title', async function() {
            expect(await window.pywebview.api.win.set_title('smoke ✓')).to.equal('smoke ✓');
        });

        it('resizes and fires resized', async function() {
            const original = await window.pywebview.api.get_size();
            const result = await window.pywebview.api.win.resize(640, 480);
            await window.pywebview.api.win.resize(original[0], original[1]);
            expect(result.event).to.have.lengthOf(2);
            expect(Math.abs(result.size[0] - 640)).to.be.below(20);
            expect(Math.abs(result.size[1] - 480)).to.be.below(20);
        });

        it('moves and fires moved', async function() {
            const result = await window.pywebview.api.win.move(120, 140);
            expect(Math.abs(result.position[0] - result.target[0])).to.be.below(20);
            expect(Math.abs(result.position[1] - result.target[1])).to.be.below(40);
        });

        it('minimizes and restores', async function() {
            expect(await window.pywebview.api.win.minimize_restore()).to.be.true;
        });

        it('maximizes and restores', async function() {
            const result = await window.pywebview.api.win.maximize_restore();
            expect(result.maximized[0]).to.be.at.least(result.before[0]);
        });

        it('toggles fullscreen', async function() {
            const result = await window.pywebview.api.win.toggle_fullscreen();
            expect(result.fullscreen[0]).to.be.at.least(result.before[0]);
            expect(Math.abs(result.after[0] - result.before[0])).to.be.below(20);
        });

        it('toggles on top', async function() {
            expect(await window.pywebview.api.win.on_top()).to.deep.equal([true, false]);
        });

        it('hides and shows', async function() {
            expect(await window.pywebview.api.win.hide_show()).to.be.true;
        });
    });

    describe('Window options', function() {
        desktopOnly();

        let plain;
        let custom;

        before(async function() {
            plain = await window.pywebview.api.win.open_with({});
            custom = await window.pywebview.api.win.open_with({
                frameless: true,
                easy_drag: true,
                shadow: false,
                x: 100,
                y: 120,
                text_select: true,
                on_top: true,
                background_color: '#2E3440',
                focus: false,
                zoomable: true,
                draggable: true,
            });
        });

        it('frameless removes the title bar', function() {
            const plainChrome = plain.size[1] - plain.inner[1];
            const customChrome = custom.size[1] - custom.inner[1];
            // Some backends (GTK) report the size without the title bar, so there is nothing to compare
            if (plainChrome <= 0) this.skip();
            expect(customChrome).to.be.below(plainChrome);
        });

        it('x and y position the window', function() {
            expect(Math.abs(custom.position[0] - 100)).to.be.below(20);
            expect(Math.abs(custom.position[1] - 120)).to.be.below(40);
        });

        it('text_select toggles text selection', function() {
            expect(plain.select).to.equal('none');
            expect(custom.select).to.not.equal('none');
        });

        it('on_top keeps the window on top', function() {
            expect(custom.on_top).to.be.true;
        });

        it('fullscreen opens the window fullscreen', async function() {
            const result = await window.pywebview.api.win.open_with({fullscreen: true});
            expect(result.size[0]).to.be.at.least(result.screen[0] * 0.9);
        });

        it('maximized opens the window maximized', async function() {
            const result = await window.pywebview.api.win.open_with({maximized: true});
            expect(result.size[0]).to.be.above(400);
        });

        it('minimized opens the window minimized and restores it', async function() {
            const result = await window.pywebview.api.win.open_with({minimized: true}, 'restore');
            expect(result.size[0]).to.be.above(0);
        });

        it('hidden opens the window hidden and shows it', async function() {
            const result = await window.pywebview.api.win.open_with({hidden: true}, 'show');
            expect(result.size[0]).to.be.above(0);
        });

        it('transparent and vibrancy open a window', async function() {
            const result = await window.pywebview.api.win.open_with({
                transparent: true,
                vibrancy: true,
            });
            expect(result.inner[0]).to.be.above(0);
        });

        it('resizable and min_size open a window', async function() {
            const result = await window.pywebview.api.win.open_with({
                resizable: false,
                min_size: [350, 250],
            });
            expect(result.inner[0]).to.be.above(0);
        });
    });

    describe('Multiple windows', function() {
        desktopOnly();

        it('opens, uses, navigates and closes a second window', async function() {
            const result = await window.pywebview.api.win.second_window();
            expect(result.title).to.equal('second');
            expect(result.api).to.equal(420);
            expect(result.windows).to.equal(info.windows + 1);
            expect(result.reloaded_title).to.equal('reloaded');
            expect(result.windows_after).to.equal(info.windows);
        });
    });
});
