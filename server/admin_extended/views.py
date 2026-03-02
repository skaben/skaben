from django.http import HttpResponse
from django.shortcuts import render
from peripheral_behavior.models.access import SkabenUser

from .forms import CSVUploadForm


def upload_csv_view(request):
    if request.method == "POST":
        form = CSVUploadForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            users = SkabenUser.objects.all()
            return render(request, "success.html", {"users": users})
    else:
        form = CSVUploadForm()
    return render(request, "upload.html", {"form": form})


def download_example_csv(request):
    # Create the CSV data as a string
    data = "user_name;user_description;access_code\n" "John Doe;Awesome user;1234\n" "Jane Smith;Cool user;6789\n"

    # Create a HttpResponse object with the CSV data as content
    response = HttpResponse(data, content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="example.csv"'
    return response
