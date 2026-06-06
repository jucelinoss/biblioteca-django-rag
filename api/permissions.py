from rest_framework import permissions


class IsBibliotecarioOrReadOnly(permissions.BasePermission):
    """
    Permissão que libera apenas métodos seguros (GET, HEAD, OPTIONS) para usuários comuns,
    e exige que o usuário esteja no grupo "Bibliotecario" ou seja superuser/staff para escrita.
    """

    def has_permission(self, request, view):
        # Métodos seguros são liberados para qualquer usuário autenticado
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated

        # Para escrita (POST, PUT, PATCH, DELETE), exige autenticação e papel de Bibliotecario
        if not (request.user and request.user.is_authenticated):
            return False

        # Verifica staff, superuser ou grupo "Bibliotecario"
        return (
            request.user.is_staff or 
            request.user.is_superuser or 
            request.user.groups.filter(name='Bibliotecario').exists()
        )
