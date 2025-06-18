describe.skip('DOM Tests', function() {
    before(async function() {
        await testUtils.waitForPywebview();

        // Set up the DOM HTML content for testing
        await window.pywebview.api.window.evaluate_js(`
            document.querySelector('#test-area').innerHTML = \`
          <div id="container">
              <div id="child1" class="test" data-id="blz" tabindex="3">DUDE</div>
              <div id="child2" class="test"></div>
              <div id="child3" class="test" style="display: none; background-color: rgb(255, 0, 0)" tabindex="2"></div>
          </div>
          <div id="container2">
              <input type="text" value="pizdec" id="input"/>
              <button id="button">Click me</button>
          </div>
            \`;
        `);
    });

    describe('Element Properties', function() {
        it('should get and set element properties', async function() {
            // Get element and check basic properties
            await window.pywebview.api.eval(`child 1 = window.dom.get_element("#child1")
              `);
            let child1 = await window.pywebview.api.dom.get_element('#child1');
            expect(child1.id).to.equal('child1');
            expect(child1.tag).to.equal('div');
            expect(child1.tabindex).to.equal(3);
            expect(child1.text).to.equal('DUDE');

            // Set text content
            await window.pywebview.api.eval('window.dom.get_element("#child1").text = "WOW"');
            child1 = await window.pywebview.api.dom.get_element('#child1');
            expect(child1.text).to.equal('WOW');

            // Set tabindex
            await window.pywebview.api.eval('window.dom.get_element("#child1").tabindex = 10');
            child1 = await window.pywebview.api.dom.get_element('#child1');
            expect(child1.tabindex).to.equal(10);

            // Test input value
            const input = await window.pywebview.api.dom.get_element('#input');
            expect(input.value).to.equal('pizdec');
            await window.pywebview.api.eval('window.dom.get_element("#input").value = "tisok"');
            const updatedInput = await window.pywebview.api.dom.get_element('#input');
            expect(updatedInput.value).to.equal('tisok');
        });
    })

    describe('CSS Classes', function() {
        it('should manipulate CSS classes', async function() {
            let child1 = await window.pywebview.api.dom.get_element('#child1');

            // Check initial classes
            expect(Array.from(child1.classes)).to.deep.equal(['test']);

            // Add class
            await window.pywebview.api.eval('window.dom.get_element("#child1").classes.append("test2")');
            child1 = await window.pywebview.api.dom.get_element('#child1');
            expect(Array.from(child1.classes)).to.deep.equal(['test', 'test2']);

            // Toggle class (remove existing)
            await window.pywebview.api.eval('window.dom.get_element("#child1").classes.toggle("test")');
            child1 = await window.pywebview.api.dom.get_element('#child1');
            expect(Array.from(child1.classes)).to.deep.equal(['test2']);

            // Toggle class (add back)
            await window.pywebview.api.eval('window.dom.get_element("#child1").classes.toggle("test")');
            child1 = await window.pywebview.api.dom.get_element('#child1');
            expect(Array.from(child1.classes)).to.deep.equal(['test2', 'test']);

            // Set classes array
            await window.pywebview.api.eval('window.dom.get_element("#child1").classes = ["woah"]');
            child1 = await window.pywebview.api.dom.get_element('#child1');
            expect(Array.from(child1.classes)).to.deep.equal(['woah']);

            // Clear classes
            await window.pywebview.api.eval('window.dom.get_element("#child1").classes.clear()');
            child1 = await window.pywebview.api.dom.get_element('#child1');
            expect(child1.classes.length).to.equal(0);
        });
    })

    describe('Element Attributes', function() {
        it('should manipulate element attributes', async function() {
            let child1 = await window.pywebview.api.dom.get_element('#child1');

            // Check initial attributes
            expect(Object.fromEntries(child1.attributes)).to.deep.equal({
                'class': 'test',
                'id': 'child1',
                'data-id': 'blz',
                'tabindex': '3'
            });

            // Get individual attribute
            expect(child1.attributes['class']).to.equal('test');

            // Get keys, values
            expect(Array.from(child1.attributes.keys())).to.include.members(['class', 'id', 'data-id', 'tabindex']);
            expect(Array.from(child1.attributes.values())).to.include.members(['test', 'child1', 'blz', '3']);

            // Test get method
            expect(child1.attributes.get('class')).to.equal('test');
            expect(child1.attributes.get('class2')).to.be.null;
            expect(child1.attributes['class2']).to.be.null;

            // Delete attribute
            await window.pywebview.api.eval('delete window.dom.get_element("#child1").attributes["class"]');
            child1 = await window.pywebview.api.dom.get_element('#child1');
            expect(Object.fromEntries(child1.attributes)).to.deep.equal({
                'id': 'child1',
                'data-id': 'blz',
                'tabindex': '3'
            });

            // Set new attribute
            await window.pywebview.api.eval('window.dom.get_element("#child1").attributes["data-test"] = "test2"');
            child1 = await window.pywebview.api.dom.get_element('#child1');
            expect(Object.fromEntries(child1.attributes)).to.deep.equal({
                'id': 'child1',
                'data-id': 'blz',
                'tabindex': '3',
                'data-test': 'test2'
            });

            // Replace all attributes
            await window.pywebview.api.eval('window.dom.get_element("#child1").attributes = {"data-test": "test3"}');
            child1 = await window.pywebview.api.dom.get_element('#child1');
            expect(child1.attributes['data-test']).to.equal('test3');

            // Clear attributes
            await window.pywebview.api.eval('window.dom.get_element("#child1").attributes.clear()');
            child1 = await window.pywebview.api.dom.get_element('#child1');
            expect(Object.keys(child1.attributes).length).to.equal(0);
        });
    });

    describe('Element Styles', function() {
        it('should manipulate element styles', async function() {
            let child3 = await window.pywebview.api.dom.get_element('#child3');

            // Check initial styles
            expect(child3.style['display']).to.equal('none');
            expect(child3.style['background-color']).to.equal('rgb(255, 0, 0)');

            // Set styles
            await window.pywebview.api.eval('window.dom.get_element("#child3").style["display"] = "flex"');
            await window.pywebview.api.eval('window.dom.get_element("#child3").style["background-color"] = "rgb(0, 0, 255)"');
            child3 = await window.pywebview.api.dom.get_element('#child3');

            expect(child3.style['display']).to.equal('flex');
            expect(child3.style['background-color']).to.equal('rgb(0, 0, 255)');

            // Clear styles
            await window.pywebview.api.eval('window.dom.get_element("#child3").style.clear()');
            child3 = await window.pywebview.api.dom.get_element('#child3');
            expect(child3.style['display']).to.equal('block');
            expect(child3.style['background-color']).to.equal('rgba(0, 0, 0, 0)');
        });
    });

    describe('Element Visibility', function() {
        it('should control element visibility', async function() {
            let child3 = await window.pywebview.api.dom.get_element('#child3');

            // Check initial visibility (should be hidden due to display: none)
            expect(child3.visible).to.be.false;

            // Show element
            await window.pywebview.api.eval('window.dom.get_element("#child3").show()');
            child3 = await window.pywebview.api.dom.get_element('#child3');
            expect(child3.visible).to.be.true;

            // Hide element
            await window.pywebview.api.eval('window.dom.get_element("#child3").hide()');
            child3 = await window.pywebview.api.dom.get_element('#child3');
            expect(child3.visible).to.be.false;

            // Toggle visibility (show)
            await window.pywebview.api.eval('window.dom.get_element("#child3").toggle()');
            child3 = await window.pywebview.api.dom.get_element('#child3');
            expect(child3.visible).to.be.true;

            // Toggle visibility (hide)
            await window.pywebview.api.eval('window.dom.get_element("#child3").toggle()');
            child3 = await window.pywebview.api.dom.get_element('#child3');
            expect(child3.visible).to.be.false;
        });
    });

    describe('Element Focus', function() {
        it('should control element focus', async function() {
            let input = await window.pywebview.api.dom.get_element('#input');

            // Check initial focus state
            expect(input.focused).to.be.false;

            // Focus element
            await window.pywebview.api.eval('window.dom.get_element("#input").focus()');
            input = await window.pywebview.api.dom.get_element('#input');
            expect(input.focused).to.be.true;

            // Blur element
            await window.pywebview.api.eval('window.dom.get_element("#input").blur()');
            input = await window.pywebview.api.dom.get_element('#input');
            expect(input.focused).to.be.false;
        });
    });

    describe('DOM Traversal', function() {
        it('should traverse DOM elements', async function() {
            const child2 = await window.pywebview.api.dom.get_element('#child2');

            // Check parent
            expect(child2.parent.id).to.equal('container');

            // Check next sibling
            expect(child2.next.id).to.equal('child3');

            // Check previous sibling
            expect(child2.previous.id).to.equal('child1');

            // Check children
            const container = await window.pywebview.api.dom.get_element('#container');
            expect(container.children.length).to.equal(3);
            expect(container.children[0].id).to.equal('child1');
            expect(container.children[1].id).to.equal('child2');
            expect(container.children[2].id).to.equal('child3');
        });
    });

    describe('DOM Manipulation', function() {
        it('should manipulate DOM elements', async function() {
            let container = await window.pywebview.api.dom.get_element('#container');
            let container2 = await window.pywebview.api.dom.get_element('#container2');

            // Check initial children count
            expect(container.children.length).to.equal(3);

            // Empty container
            await window.pywebview.api.eval('window.dom.get_element("#container").empty()');
            container = await window.pywebview.api.dom.get_element('#container');
            expect(container.children).to.deep.equal([]);

            // Append HTML
            await window.pywebview.api.eval('window.dom.get_element("#container").append(\'<div id="child1"></div>\')');
            container = await window.pywebview.api.dom.get_element('#container');
            expect(container.children.length).to.equal(1);
            expect(container.children[0].id).to.equal('child1');

            // Create element
            const child2 = await window.pywebview.api.dom.create_element('<div id="child2" class="child-class">CHILD</div>', container);
            container = await window.pywebview.api.dom.get_element('#container');
            expect(container.children.length).to.equal(2);
            expect(container.children[1].id).to.equal('child2');
            expect(child2.parent.id).to.equal('container');
            expect(child2.id).to.equal('child2');

            // Copy element (need to use eval for method calls that return elements)
            await window.pywebview.api.eval(`
                const child2 = window.dom.get_element("#child2");
                const container2 = window.dom.get_element("#container2");
                const child3 = child2.copy(container2);
                window.testChild3Id = child3.id || '';
            `);
            container2 = await window.pywebview.api.dom.get_element('#container2');
            expect(container2.children.length).to.equal(3); // input, button, + copied div
            expect(container2.children[2].text).to.equal('CHILD');

            const child3 = container2.children[2];
            expect(Array.from(child3.classes)).to.deep.equal(['child-class']);
            const testChild3Id = await window.pywebview.api.window.evaluate_js('window.testChild3Id');
            expect(testChild3Id).to.equal(''); // ID should be cleared on copy

            // Copy without parent (should copy to current parent)
            await window.pywebview.api.eval(`
                const child2 = window.dom.get_element("#child2");
                child2.copy();
            `);
            container = await window.pywebview.api.dom.get_element('#container');
            expect(container.children.length).to.equal(3);

            // Move element
            await window.pywebview.api.eval(`
                const container = window.dom.get_element("#container");
                const container2 = window.dom.get_element("#container2");
                container.children[2].move(container2);
            `);
            container = await window.pywebview.api.dom.get_element('#container');
            container2 = await window.pywebview.api.dom.get_element('#container2');
            expect(container.children.length).to.equal(2);
            expect(container2.children.length).to.equal(4);

            // Remove element
            await window.pywebview.api.eval(`
                const container = window.dom.get_element("#container");
                container.children[0].remove();
            `);
            container = await window.pywebview.api.dom.get_element('#container');
            expect(container.children.length).to.equal(1);
            expect(container.children[0].id).to.equal('child2');
        });
    });

    describe('DOM Manipulation Modes', function() {
        it('should handle different manipulation modes', async function() {

            const child1 = await window.pywebview.api.dom.get_element('#child1');
            const child2 = await window.pywebview.api.dom.get_element('#child2');
            const child3 = await window.pywebview.api.dom.get_element('#child3');
            let container2 = await window.pywebview.api.dom.get_element('#container2');

            // Move as first child
            await window.pywebview.api.eval(`
                const child1 = window.dom.get_element("#child1");
                const container2 = window.dom.get_element("#container2");
                child1.move(container2, window.dom.ManipulationMode.FirstChild);
            `);
            container2 = await window.pywebview.api.dom.get_element('#container2');
            expect(container2.children[0].id).to.equal('child1');

            // Move as last child
            await window.pywebview.api.eval(`
                const child2 = window.dom.get_element("#child2");
                const container2 = window.dom.get_element("#container2");
                child2.move(container2, window.dom.ManipulationMode.LastChild);
            `);
            container2 = await window.pywebview.api.dom.get_element('#container2');
            expect(container2.children[container2.children.length - 1].id).to.equal('child2');

            // Move before another element
            await window.pywebview.api.eval(`
                const child3 = window.dom.get_element("#child3");
                const child1 = window.dom.get_element("#child1");
                child3.move(child1, window.dom.ManipulationMode.Before);
            `);
            container2 = await window.pywebview.api.dom.get_element('#container2');
            expect(container2.children[0].id).to.equal('child3');

            // Move after another element
            await window.pywebview.api.eval(`
                const child1 = window.dom.get_element("#child1");
                const child2 = window.dom.get_element("#child2");
                child1.move(child2, window.dom.ManipulationMode.After);
            `);
            container2 = await window.pywebview.api.dom.get_element('#container2');
            expect(container2.children[container2.children.length - 1].id).to.equal('child1');

            // Replace element
            await window.pywebview.api.eval(`
                const child2 = window.dom.get_element("#child2");
                const container2 = window.dom.get_element("#container2");
                child2.move(container2, window.dom.ManipulationMode.Replace);
            `);
            expect(await window.pywebview.api.dom.get_element('#container2')).to.be.null;
            const child2Updated = await window.pywebview.api.dom.get_element('#child2');
            expect(child2Updated.parent.tag).to.equal('body');
        });
    });

    describe('DOM Events', function() {
        it('should handle DOM events', async function() {

            const button = await window.pywebview.api.dom.get_element('#button');

            // Set up a variable to track button clicks
            await window.pywebview.api.window.evaluate_js('window.buttonClickCount = 0;');

            // Add click event listener
            await window.pywebview.api.eval(`
                const button = window.dom.get_element("#button");
                function clickHandler(event) {
                    if (event.target.id === 'button') {
                        window.buttonClickCount++;
                    }
                }
                window.testClickHandler = clickHandler;
                button.events.click += clickHandler;
            `);

            // Trigger click event
            await window.pywebview.api.window.evaluate_js('document.getElementById("button").click()');

            // Wait for event to process
            await testUtils.wait(100);

            const clickCount = await window.pywebview.api.window.evaluate_js('window.buttonClickCount');
            expect(clickCount).to.equal(1);

            // Remove event listener
            await window.pywebview.api.eval(`
                const button = window.dom.get_element("#button");
                button.events.click -= window.testClickHandler;
            `);

            // Reset counter and click again
            await window.pywebview.api.window.evaluate_js('window.buttonClickCount = 0;');
            await window.pywebview.api.window.evaluate_js('document.getElementById("button").click()');

            // Wait for potential event
            await testUtils.wait(100);

            const clickCountAfterRemove = await window.pywebview.api.window.evaluate_js('window.buttonClickCount');
            expect(clickCountAfterRemove).to.equal(0);

            // Verify event handlers are cleaned up
            const handlersEmpty = await window.pywebview.api.window.evaluate_js('Object.keys(pywebview._eventHandlers).length === 0');
            expect(handlersEmpty).to.be.true;
        });
    });
});