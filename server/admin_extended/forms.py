import csv

from django import forms
from peripheral_behavior.models import AccessCode, SkabenUser


class CSVUploadForm(forms.Form):
    csv_file = forms.FileField()

    def clean_csv_file(self):
        csv_file = self.cleaned_data["csv_file"]
        if not csv_file.name.endswith(".csv"):
            raise forms.ValidationError("Invalid file format: Only CSV files are allowed.")
        return csv_file

    def save(self):
        csv_file = self.cleaned_data["csv_file"]
        decoded_file = csv_file.read().decode("utf-8").splitlines()
        reader = csv.DictReader(decoded_file, delimiter=";")
        for row in reader:
            # Validate row data
            try:
                user_name = row["user_name"]
                user_description = row["user_description"]
                access_code = row["access_code"]
            except KeyError:
                raise forms.ValidationError("Invalid CSV format: missing column(s).")
            if not all([user_name, user_description, access_code]):
                raise forms.ValidationError("Invalid CSV format: missing data.")
            user = SkabenUser(name=user_name, description=user_description)
            user.save()

            access_code = AccessCode(code=access_code, user=user)
            access_code.save()
