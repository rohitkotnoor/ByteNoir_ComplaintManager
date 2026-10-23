from django.shortcuts import render


def custom_403(request, exception=None):
    return render(request, "errors/access_denied.html", status=403)


def custom_404(request, exception=None):
    return render(request, "errors/404.html", status=404)
