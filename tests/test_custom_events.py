import webview

from .util import run_test


def test_custom_events_add_remove():
    """Test adding and removing custom event listeners"""
    window = webview.create_window('Custom Events Test', html='<html><body>TEST</body></html>')
    run_test(webview, window, custom_events_add_remove)


def test_custom_events_multiple_listeners():
    """Test multiple listeners for the same custom event"""
    window = webview.create_window('Custom Events Test', html='<html><body>TEST</body></html>')
    run_test(webview, window, custom_events_multiple_listeners)


def test_custom_events_trigger():
    """Test triggering custom events manually"""
    window = webview.create_window('Custom Events Test', html='<html><body>TEST</body></html>')
    run_test(webview, window, custom_events_trigger)


def test_custom_events_with_data():
    """Test custom events with data parameters"""
    window = webview.create_window('Custom Events Test', html='<html><body>TEST</body></html>')
    run_test(webview, window, custom_events_with_data)


# Global variables to track test results
test_results = {
    'listener1_called': False,
    'listener2_called': False,
    'listener3_called': False,
    'received_data': None,
    'call_count': 0
}


def reset_test_results():
    """Reset test results for a clean test"""
    global test_results
    test_results = {
        'listener1_called': False,
        'listener2_called': False,
        'listener3_called': False,
        'received_data': None,
        'call_count': 0
    }


def test_listener1(data=None):
    """Test listener function 1"""
    global test_results
    test_results['listener1_called'] = True
    test_results['received_data'] = data
    test_results['call_count'] += 1


def test_listener2(data=None):
    """Test listener function 2"""
    global test_results
    test_results['listener2_called'] = True
    test_results['received_data'] = data
    test_results['call_count'] += 1


def test_listener3(data=None):
    """Test listener function 3"""
    global test_results
    test_results['listener3_called'] = True
    test_results['received_data'] = data
    test_results['call_count'] += 1


def custom_events_add_remove(window):
    """Test adding and removing custom event listeners"""
    reset_test_results()
    
    # Add listener to custom event
    window.events.test_custom_event += test_listener1
    
    # Verify listener was added
    assert len(window.events.test_custom_event) == 1, "Listener should be added"
    
    # Trigger the event
    window.events.test_custom_event("test data")
    
    # Check that listener was called
    assert test_results['listener1_called'], "Listener 1 should have been called"
    assert test_results['received_data'] == "test data", "Data should be passed correctly"
    
    # Remove the listener
    window.events.test_custom_event -= test_listener1
    
    # Verify listener was removed
    assert len(window.events.test_custom_event) == 0, "Listener should be removed"
    
    # Reset and trigger again - should not be called
    reset_test_results()
    window.events.test_custom_event("test data 2")
    
    assert not test_results['listener1_called'], "Listener should not be called after removal"


def custom_events_multiple_listeners(window):
    """Test multiple listeners for the same custom event"""
    reset_test_results()
    
    # Add multiple listeners
    window.events.multi_test_event += test_listener1
    window.events.multi_test_event += test_listener2
    window.events.multi_test_event += test_listener3
    
    # Verify all listeners were added
    assert len(window.events.multi_test_event) == 3, "All 3 listeners should be added"
    
    # Trigger the event
    window.events.multi_test_event("multi test")
    
    # Check that all listeners were called
    assert test_results['listener1_called'], "Listener 1 should have been called"
    assert test_results['listener2_called'], "Listener 2 should have been called"
    assert test_results['listener3_called'], "Listener 3 should have been called"
    assert test_results['call_count'] == 3, "All 3 listeners should have been called"
    
    # Remove middle listener
    window.events.multi_test_event -= test_listener2
    assert len(window.events.multi_test_event) == 2, "Should have 2 listeners after removal"
    
    # Reset and trigger again
    reset_test_results()
    window.events.multi_test_event("multi test 2")
    
    # Check that only remaining listeners were called
    assert test_results['listener1_called'], "Listener 1 should still be called"
    assert not test_results['listener2_called'], "Listener 2 should not be called after removal"
    assert test_results['listener3_called'], "Listener 3 should still be called"
    assert test_results['call_count'] == 2, "Only 2 listeners should have been called"


def custom_events_trigger(window):
    """Test triggering custom events manually"""
    reset_test_results()
    
    # Add listener
    window.events.trigger_test_event += test_listener1
    
    # Test triggering with __call__ method
    window.events.trigger_test_event()
    
    assert test_results['listener1_called'], "Listener should be called when event is triggered"
    assert test_results['received_data'] is None, "No data should be passed when called without parameters"


def custom_events_with_data(window):
    """Test custom events with different types of data"""
    reset_test_results()
    
    window.events.data_test_event += test_listener1
    
    # Test with string data
    window.events.data_test_event("string data")
    assert test_results['received_data'] == "string data", "String data should be passed correctly"
    
    reset_test_results()
    
    # Test with numeric data
    window.events.data_test_event(42)
    assert test_results['received_data'] == 42, "Numeric data should be passed correctly"
    
    reset_test_results()
    
    # Test with dictionary data
    test_dict = {"key": "value", "number": 123}
    window.events.data_test_event(test_dict)
    assert test_results['received_data'] == test_dict, "Dictionary data should be passed correctly"
