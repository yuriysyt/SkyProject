from rest_framework import viewsets
from core.models import HealthCheck
from core.serializers import HealthCheckSerializer

class HealthCheckViewSet(viewsets.ModelViewSet):
    queryset = HealthCheck.objects.all()
    serializer_class = HealthCheckSerializer

