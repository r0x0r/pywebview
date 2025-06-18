
describe('Window tests', function() {
    before(async function() {
        await testUtils.waitForPywebview();
        window.testValue = 420;
    });

    describe('Window size tests', function() {
      it('get_size returns the correct window size', async function() {
        const size = await window.pywebview.api.get_size();
        expect(size).to.be.an('array').that.has.lengthOf(2);
        expect(size[0]).to.be.a('number'); // width
        expect(size[1]).to.be.a('number'); // height
        expect(size[0]).to.be.greaterThan(0);
        expect(size[1]).to.be.greaterThan(0);
      });
    });

    describe('Evaluate JS tests', function() {
      it('evaluate_js can run Javascript', async function() {
        expect(await window.pywebview.api.window.evaluate_js('window.testValue + 1')).to.equal(421);
      })

      it('evaluate_js can handle mixed code with functions and comments', async function() {
        const result = await window.pywebview.api.window.evaluate_js(`
          // comment
          function test() {
              return 2 + 2;
          }
          test();
        `);
        expect(result).to.equal(4);
      });

      it('evaluate_js can return arrays with mixed types', async function() {
        const result = await window.pywebview.api.window.evaluate_js(`
          function getValue() {
              return [undefined, 1, 'two', 3.00001, {four: true}]
          }
          getValue()
        `);
        expect(result).to.deep.equal([null, 1, 'two', 3.00001, {'four': true}]);
      });

      it('evaluate_js can return objects with nested structures', async function() {
        const result = await window.pywebview.api.window.evaluate_js(`
          function getValue() {
              return {1: 2, 'test': true, obj: {2: false, 3: 3.1}}
          }
          getValue()
        `);
        expect(result).to.deep.equal({'1': 2, 'test': true, 'obj': {'2': false, '3': 3.1}});
      });

      it('evaluate_js can return strings', async function() {
        const result = await window.pywebview.api.window.evaluate_js(`
          function getValue() {
              return "this is only a test"
          }
          getValue()
        `);
        expect(result).to.equal('this is only a test');
      });

      it('evaluate_js can return integers', async function() {
        const result = await window.pywebview.api.window.evaluate_js(`
          function getValue() {
              return 23
          }
          getValue()
        `);
        expect(result).to.equal(23);
      });

      it('evaluate_js can return floats', async function() {
        const result = await window.pywebview.api.window.evaluate_js(`
          function getValue() {
              return 23.23443
          }
          getValue()
        `);
        expect(result).to.equal(23.23443);
      });

      it('evaluate_js converts undefined to null', async function() {
        const result = await window.pywebview.api.window.evaluate_js(`
          function getValue() {
              return undefined
          }
          getValue()
        `);
        expect(result).to.be.null;
      });

      it('evaluate_js returns null values', async function() {
        const result = await window.pywebview.api.window.evaluate_js(`
          function getValue() {
              return null
          }
          getValue()
        `);
        expect(result).to.be.null;
      });

      it('evaluate_js converts NaN to null', async function() {
        const result = await window.pywebview.api.window.evaluate_js(`
          function getValue() {
              return NaN
          }
          getValue()
        `);
        expect(result).to.be.null;
      });

      it('evaluate_js can access DOM body element', async function() {
        const result = await window.pywebview.api.window.evaluate_js('document.body');
        expect(result).to.be.an('object');
        expect(result.nodeName).to.equal('BODY');
      });

      it('evaluate_js can access document object', async function() {
        const result = await window.pywebview.api.window.evaluate_js('document');
        expect(result).to.be.an('object');
        expect(result.nodeName).to.equal('#document');
      });

      it('evaluate_js can query DOM elements', async function() {
        // First add a test element to the DOM
        await window.pywebview.api.window.evaluate_js(`
          const testDiv = document.createElement('div');
          testDiv.id = 'testNode';
          document.body.appendChild(testDiv);
        `);

        // Then query it
        const node = await window.pywebview.api.window.evaluate_js('document.querySelector("#testNode")');
        expect(node).to.be.an('object');
        expect(node.id).to.equal('testNode');
      });

      it('evaluate_js throws exception for invalid JavaScript', async function() {
        try {
          await window.pywebview.api.window.evaluate_js('eklmn');
          expect.fail('Expected an exception to be thrown');
        } catch (error) {
          expect(error).to.be.an('error');
          // The exact error message may vary between implementations
          expect(error.message).to.include('ReferenceError') || expect(error.message).to.include('eklmn');
        }
      });

    })
    describe('Cookie tests', function() {
      beforeEach(function() {
        testUtils.setCookie('testCookie1', 'value1');
        testUtils.setCookie('testCookie2', 'value2');
        testUtils.setCookie('testJson', JSON.stringify({key: 'value', number: 42}));
      });

      it('get_cookies returns cookies', async function() {
        const cookies = await window.pywebview.api.get_cookies();
        expect(cookies).to.be.an('array').that.has.lengthOf(3);
        const cookieNames = cookies.map(c => {
          // Extract cookie name from Set-Cookie header
          const match = c.match(/^Set-Cookie: ([^=]+)=/);
          return match ? match[1] : null;
        }).filter(Boolean);

        expect(cookieNames).to.include.members(['testCookie1', 'testCookie2', 'testJson']);
      });

      it('clear_cookies clears all cookies', async function() {
        const cookies = await window.pywebview.api.get_cookies();
        expect(cookies).to.be.an('array').that.has.lengthOf(3);
        await window.pywebview.api.clear_cookies();
        const clearedCookies = await window.pywebview.api.get_cookies();
        expect(clearedCookies).to.be.an('array').that.is.empty;
      })
    });

})