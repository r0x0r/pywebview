// Python DOM API (window.dom) driven through api.dom (see DomAPI in main.py)
describe('DOM tests', function() {
    after(function() {
        document.getElementById('dom-sandbox').innerHTML = '';
    });

    it('creates and queries elements', async function() {
        const result = await window.pywebview.api.dom.create_and_query();
        expect(result).to.deep.equal({
            count: 3,
            children: 3,
            tag: 'li',
            text: 'item 1',
            parent: 'dom-list',
            next: 'item 1',
            previous: 'item 1',
        });
    });

    it('manipulates text, classes, style, attributes and visibility', async function() {
        const result = await window.pywebview.api.dom.manipulate();
        expect(result).to.deep.equal({
            text: 'after',
            hasClass: true,
            color: 'rgb(255, 0, 0)',
            attribute: 'yes',
            copy: true,
            hidden: true,
            visible: true,
            copy_removed: true,
        });
    });

    it('delivers DOM events to Python', async function() {
        const result = await window.pywebview.api.dom.events();
        expect(result).to.deep.equal({fired: true, target: 'dom-button'});
    });
});
