from django.shortcuts import render
from django.http import HttpResponse
from myapp.forms import DateSelectionForm
from myapp.models import DailyRecord

def export(request):
    if request.method == 'POST':
        form = DateSelectionForm(request.POST)
        if form.is_valid():
            selected_date = form.cleaned_data['selected_date']

            data = DailyRecord.objects.filter(date=selected_date)


            sql_content = "\n".join([obj.to_sql() for obj in data])


            response = HttpResponse(sql_content, content_type='application/sql')
            response['Content-Disposition'] = f'attachment; filename=export_{selected_date}.sql'
            return response
    else:
        form = DateSelectionForm()

    return render(request, 'myapp/export.html', {'form': form})



def export_data_afternoon(request):
    if request.method == 'POST':
        form = DateSelectionForm(request.POST)
        if form.is_valid():
            selected_date = form.cleaned_data['selected_date']

            data = DailyRecord.objects.filter(date=selected_date)


            sql_content = "\n".join([obj.to_sql_all() for obj in data])


            response = HttpResponse(sql_content, content_type='application/sql')
            response['Content-Disposition'] = f'attachment; filename=export_{selected_date}.sql'
            return response
    else:
        form = DateSelectionForm()

    return render(request, 'myapp/export.html', {'form': form})
