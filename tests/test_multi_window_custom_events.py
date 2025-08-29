import webview
import threading
import time

from .util import run_test


def test_custom_events_multiple_windows():
    """Test custom events in multiple windows"""
    main_window = webview.create_window('Main Window Test', html='<html><body>MAIN</body></html>')
    run_test(webview, main_window, custom_events_multiple_windows)


def test_custom_events_cross_window():
    """Test that custom events are isolated between windows"""
    main_window = webview.create_window('Cross Window Test', html='<html><body>MAIN</body></html>')
    run_test(webview, main_window, custom_events_cross_window_isolation)


def test_custom_events_secondary_window_lifecycle():
    """Test custom events during secondary window creation and destruction"""
    main_window = webview.create_window('Lifecycle Test', html='<html><body>MAIN</body></html>')
    run_test(webview, main_window, custom_events_secondary_window_lifecycle)


# Global variables to track test results across windows
multi_window_results = {
    'main_events': [],
    'secondary_events': [],
    'main_listener_called': False,
    'secondary_listener_called': False,
    'cross_contamination': False
}


def reset_multi_window_results():
    """Reset test results for clean testing"""
    global multi_window_results
    multi_window_results = {
        'main_events': [],
        'secondary_events': [],
        'main_listener_called': False,
        'secondary_listener_called': False,
        'cross_contamination': False
    }


def main_window_listener(data=None):
    """Listener for main window events"""
    global multi_window_results
    multi_window_results['main_events'].append(data)
    multi_window_results['main_listener_called'] = True


def secondary_window_listener(data=None):
    """Listener for secondary window events"""
    global multi_window_results
    multi_window_results['secondary_events'].append(data)
    multi_window_results['secondary_listener_called'] = True


def cross_contamination_detector(data=None):
    """Detector for cross-window event contamination"""
    global multi_window_results
    multi_window_results['cross_contamination'] = True


def custom_events_multiple_windows(main_window):
    """Test custom events functionality in multiple windows"""
    reset_multi_window_results()
    
    # Create secondary window
    secondary_window = webview.create_window(
        'Secondary Window Test', 
        html='<html><body>SECONDARY</body></html>',
        width=300,
        height=200
    )
    
    # Wait for secondary window to be ready
    time.sleep(1)
    
    # Add listeners to both windows
    main_window.events.test_event += main_window_listener
    secondary_window.events.test_event += secondary_window_listener
    
    # Verify listeners were added
    assert len(main_window.events.test_event) == 1, "Main window should have 1 listener"
    assert len(secondary_window.events.test_event) == 1, "Secondary window should have 1 listener"
    
    # Trigger events in both windows
    main_window.events.test_event("main_data")
    secondary_window.events.test_event("secondary_data")
    
    # Wait for events to process
    time.sleep(0.5)
    
    # Verify events were handled correctly
    assert multi_window_results['main_listener_called'], "Main window listener should be called"
    assert multi_window_results['secondary_listener_called'], "Secondary window listener should be called"
    assert "main_data" in multi_window_results['main_events'], "Main window should receive main_data"
    assert "secondary_data" in multi_window_results['secondary_events'], "Secondary window should receive secondary_data"
    
    # Test removing listeners
    main_window.events.test_event -= main_window_listener
    assert len(main_window.events.test_event) == 0, "Main window should have no listeners after removal"
    assert len(secondary_window.events.test_event) == 1, "Secondary window should still have 1 listener"
    
    # Clean up
    secondary_window.destroy()


def custom_events_cross_window_isolation(main_window):
    """Test that custom events are properly isolated between windows"""
    reset_multi_window_results()
    
    # Create secondary window
    secondary_window = webview.create_window(
        'Isolation Test Window', 
        html='<html><body>ISOLATION_TEST</body></html>',
        width=300,
        height=200
    )
    
    time.sleep(1)
    
    # Add listener only to main window
    main_window.events.isolation_test += main_window_listener
    
    # Add cross-contamination detector to secondary window  
    secondary_window.events.isolation_test += cross_contamination_detector
    
    # Trigger event only in main window
    main_window.events.isolation_test("main_only_data")
    
    time.sleep(0.5)
    
    # Verify that main window received the event
    assert multi_window_results['main_listener_called'], "Main window should receive its event"
    assert "main_only_data" in multi_window_results['main_events'], "Main window should have correct data"
    
    # Verify that secondary window did NOT receive the event
    assert not multi_window_results['cross_contamination'], "Secondary window should not receive main window events"
    
    # Reset and test the opposite direction
    reset_multi_window_results()
    
    # Trigger event only in secondary window
    secondary_window.events.isolation_test("secondary_only_data")
    
    time.sleep(0.5)
    
    # Verify that main window did NOT receive the secondary event
    assert not multi_window_results['main_listener_called'], "Main window should not receive secondary window events"
    assert multi_window_results['cross_contamination'], "Secondary window should receive its own event"
    
    # Clean up
    secondary_window.destroy()


def custom_events_secondary_window_lifecycle(main_window):
    """Test custom events during secondary window creation and destruction"""
    reset_multi_window_results()
    
    # Create secondary window
    secondary_window = webview.create_window(
        'Lifecycle Test Window', 
        html='<html><body>LIFECYCLE_TEST</body></html>',
        width=300,
        height=200
    )
    
    time.sleep(1)
    
    # Add listener to secondary window
    secondary_window.events.lifecycle_test += secondary_window_listener
    
    # Verify listener was added
    assert len(secondary_window.events.lifecycle_test) == 1, "Secondary window should have 1 listener"
    
    # Trigger event in secondary window
    secondary_window.events.lifecycle_test("lifecycle_data")
    
    time.sleep(0.5)
    
    # Verify event was handled
    assert multi_window_results['secondary_listener_called'], "Secondary window listener should be called"
    assert "lifecycle_data" in multi_window_results['secondary_events'], "Secondary window should receive correct data"
    
    # Test that events work with multiple listeners
    def additional_listener(data):
        multi_window_results['secondary_events'].append(f"additional_{data}")
    
    secondary_window.events.lifecycle_test += additional_listener
    assert len(secondary_window.events.lifecycle_test) == 2, "Secondary window should have 2 listeners"
    
    # Reset and trigger again
    reset_multi_window_results()
    secondary_window.events.lifecycle_test("multi_listener_data")
    
    time.sleep(0.5)
    
    # Verify both listeners were called
    assert multi_window_results['secondary_listener_called'], "Original listener should still work"
    assert "multi_listener_data" in multi_window_results['secondary_events'], "Should receive original data"
    assert "additional_multi_listener_data" in multi_window_results['secondary_events'], "Should receive additional listener data"
    
    # Clean up
    secondary_window.destroy()
    
    # After destruction, verify that we can't trigger events (should not crash)
    try:
        secondary_window.events.lifecycle_test("after_destroy")
        # If no exception is raised, that's also acceptable behavior
    except Exception as e:
        # If an exception is raised, it should be a reasonable one
        assert isinstance(e, (AttributeError, RuntimeError, webview.errors.WebViewException)), f"Unexpected exception type: {type(e)}"
