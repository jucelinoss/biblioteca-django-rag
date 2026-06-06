from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
)

from .views import (
    PessoaViewSet,
    LivroViewSet,
    EmprestimoViewSet,
    RecomendacaoIAView,
    ChatIAView,
    DashboardClienteView,
)

router = DefaultRouter()
router.register(r'pessoas', PessoaViewSet, basename='pessoa')
router.register(r'livros', LivroViewSet, basename='livro')
router.register(r'emprestimos', EmprestimoViewSet, basename='emprestimo')

urlpatterns = [
    # Autenticação
    path('auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # Serviços de IA
    path('ia/recomendar/', RecomendacaoIAView.as_view(), name='ia_recomendar'),
    path('ia/chat/', ChatIAView.as_view(), name='ia_chat'),

    # CRUD (Pessoas, Livros, Empréstimos)
    path('', include(router.urls)),

    # Documentação OpenAPI / Swagger
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    path('docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),

    # Dashboard Cliente SPA
    path('dashboard-cliente/', DashboardClienteView.as_view(), name='dashboard_cliente'),
]
