import csv
from django.http import HttpResponse
from django.views import View
from core.models import HealthCheck

class ExportHealthCheckCSV(View):
    def get(self, request, *args, **kwargs):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="health_checks.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Date', 'Department', 'Category', 'Score', 'Comment'])
        
        for check in HealthCheck.objects.all():
            writer.writerow([
                check.created_at.strftime('%Y-%m-%d'),
                check.department.name,
                check.category.name,
                check.score,
                check.comment
            ])
        
        return response

