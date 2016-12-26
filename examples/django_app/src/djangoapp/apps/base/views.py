from django.shortcuts import render


# Create your views here.
def index(request):
    replacements = {}
    return render(request, "base/index.html", replacements)