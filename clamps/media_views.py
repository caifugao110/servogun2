from django.conf import settings
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
import os

@login_required
def protected_media(request, path):
    """
    View to serve protected media files, requiring user authentication.
    """
    file_path = os.path.join(settings.MEDIA_ROOT, path)
    if not os.path.exists(file_path):
        raise Http404("File not found")

    # Ensure the requested path is within MEDIA_ROOT to prevent directory traversal
    if not os.path.abspath(file_path).startswith(os.path.abspath(settings.MEDIA_ROOT)):
        raise Http404("File not found")

    response = FileResponse(open(file_path, 'rb'))
    response['Content-Disposition'] = f'inline; filename="{os.path.basename(file_path)}"'
    return response


