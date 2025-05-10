# DOM support

Starting from 5.0 _pywebview_ has got support for basic DOM manipulation, traversal operations and DOM events. See these examples for details [DOM Events](/examples/dom_events), [DOM Manipulation](/examples/dom_manipulation) and [DOM Traversal](/examples/dom_traversal).

## Create element

``` python
element = window.dom.create_element('<div>new element</div>') # insert a new element as body's last child
element = window.dom.create_element('<h1>Warning</h1>' parent='#container', mode=ManipulationMode.FirstChild) # insert a new element to #containaer as a first child
```

Manipulation Mode can be one of following `LastChild`, `FirstChild`, `Before`, `After` or `Replace`. `LastChild` is a default value.

## Get elements

``` python
element = window.dom.get_element('#element-id') # returns a first matching Element or None
elements = window.dom.get_elements('div') # returns a list of matching Elements
```

## Basic information about element

``` python
element.id # return element's id
element.classes # return a list like object of element's classes
element.style # return a dict like object of element's styles
element.tabindex # return element's tab index
element.tag # return element's tag name
element.text # return element's text content
element.value # return input element's value
```

Some element's properties can be set or modified

``` python
element.id = 'new-id'
element.classes.add('green-text') # add .green-text class
element.classes.remove('red-background') # remove .red-background class
element.classes.toggle('blue-border') # toggle .blue-border class
element.style['width'] = '200px'
element.tabindex = 108
element.text = 'New content'
element.value = 'Luna'
```

## Manupulate element

``` python
new_container = window.get_element('#new-container')
new_element = element.copy() # copies element as the parent's last child
yet_another_element = new_element.copy(new_container, webview.dom.ManipulationMode.FirstChild, "new-id") # copies element to #new-container as a first child
yet_another_element = yet_another_element.move('#new-container2') # moves element to #new-container2 as a last child
yet_another_element.remove() # remove element
new_container.empty() # empty #new-container from its children
new_container.append('<span>kick-ass content</span>') # append new DOM to #new-container
```

## Traversal

```python
element.children # return a list of element's children
element.next # return a next element in the DOM hierarchy or None
element.parent # return element's parent
element.previous # return a previous element in the DOM hierarchy or None
```

`body`, `document` and `window` objects can be directly accessed via

```python
window.dom.body
window.dom.document
window.dom.window
```

### Element visibility and focus

``` python
element.hide() # hide element
print(element.visible) # False
element.show() # show element
print(element.visible) # True
element.toggle() # toggle visibility
element.focus() # focus element
print(element.focused) # True if element can be focused
element.blur() # blur element
print(element.focused) # False
```

## Events

DOM events can be subscribed directly from Python

``` python
def print_handler(e):
  print(e)

def shout_handler(e):
  print('!!!!!!!!')
  print(e)
  print('!!!!!!!!')

element.on('click', print_handler)
element.events.click += shout_handler # these two ways to subscribe to an event are equivalent

element.off('click', print_handler)
element.events.click -= shout_handler # as well as these two
```

If you need more control over how DOM events are handled, you can use `webview.dom.DOMEventHandler`. It allows setting `preventDefault`, `stopPropagation`, `stopImmediatePropagation` values, as well as
debouncing event handlers.

```python
window.dom.document.events.dragover += DOMEventHandler(on_drag, prevent_default=True, stop_propagation=True, stop_immediate_propagation=True, debounce=500)
```

_pywebview_ enhances the `drop` event to support full file path information.

``` python
window.dom.document.events.drop += lambda e: print(e['domTransfer']['files'][0]) # print a full path of the dropped file
```
