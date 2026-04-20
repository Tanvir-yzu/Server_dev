from django.shortcuts import render
from django.contrib import messages

def test_messages_view(request):
    """Test view to trigger all message types for toast validation."""
    # Optional: add messages manually if you want to test server-side flow
    # messages.success(request, 'Server-side success message!')
    # messages.error(request, 'Server-side error message!')
    # messages.warning(request, 'Server-side warning message!')
    # messages.info(request, 'Server-side info message!')
    return render(request, 'DevOps/test_messages.html')