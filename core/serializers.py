from rest_framework import serializers
from core.models import HealthCheck

class HealthCheckSerializer(serializers.ModelSerializer):
    class Meta:
        model = HealthCheck
        fields = '__all__'

