"""
Views Package - The 'V' in MVC

This package contains all view-related code:
- HTML templates for the web UI
- Template rendering utilities
- Static asset management

In a traditional MVC framework, views handle presentation logic.
For this FastAPI application, views are primarily:
1. HTML templates served to the browser
2. The frontend JavaScript that renders the UI

The actual rendering is done client-side with JavaScript,
making this a "thin view" approach where the server provides
the initial HTML shell and the client handles dynamic updates.
"""
