from rest_framework import viewsets, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Avg
from core.models import HealthCheck, Department, Category
from core.serializers import HealthCheckSerializer, DepartmentSerializer, CategorySerializer

class HealthCheckViewSet(viewsets.ModelViewSet):
    queryset = HealthCheck.objects.all()
    serializer_class = HealthCheckSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['department__name', 'category__name', 'comment']
    ordering_fields = ['created_at', 'score', 'department__name', 'category__name']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by department
        department_id = self.request.query_params.get('department')
        if department_id:
            queryset = queryset.filter(department_id=department_id)
        
        # Filter by category
        category_id = self.request.query_params.get('category')
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(created_at__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__lte=end_date)
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        Get statistics about health checks.
        department_id = request.query_params.get('department')
        category_id = request.query_params.get('category')
        
        queryset = self.get_queryset()
        
        # Calculate statistics
        avg_score = queryset.aggregate(avg_score=Avg('score'))['avg_score'] or 0
        
        # Get scores by department
        dept_scores = []
        departments = Department.objects.all()
        if department_id:
            departments = departments.filter(id=department_id)
            
        for dept in departments:
            dept_checks = queryset.filter(department=dept)
            if dept_checks.exists():
                avg_dept_score = dept_checks.aggregate(avg=Avg('score'))['avg'] or 0
                dept_scores.append({
                    'id': dept.id,
                    'name': dept.name,
                    'avg_score': round(avg_dept_score, 1),
                    'count': dept_checks.count()
                })
        
        # Get scores by category
        cat_scores = []
        categories = Category.objects.all()
        if category_id:
            categories = categories.filter(id=category_id)
            
        for cat in categories:
            cat_checks = queryset.filter(category=cat)
            if cat_checks.exists():
                avg_cat_score = cat_checks.aggregate(avg=Avg('score'))['avg'] or 0
                cat_scores.append({
                    'id': cat.id,
                    'name': cat.name,
                    'avg_score': round(avg_cat_score, 1),
                    'count': cat_checks.count()
                })
        
        return Response({
            'avg_score': round(avg_score, 1),
            'total_count': queryset.count(),
            'departments': dept_scores,
            'categories': cat_scores
        })

class DepartmentViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer
    permission_classes = [permissions.IsAuthenticated]

class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticated]

