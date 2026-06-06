import logging
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError as DRFValidationError

logger = logging.getLogger('api')

def custom_exception_handler(exc, context):
    # Tratar Django ValidationError para retornar como DRFValidationError (HTTP 400)
    if isinstance(exc, DjangoValidationError):
        if hasattr(exc, 'message_dict'):
            exc = DRFValidationError(detail=exc.message_dict)
        elif hasattr(exc, 'messages'):
            exc = DRFValidationError(detail=exc.messages)
        else:
            exc = DRFValidationError(detail=str(exc))

    # Executa o exception_handler padrão do DRF
    response = exception_handler(exc, context)

    # Se a resposta do DRF existir (erros tratados pelo framework)
    if response is not None:
        status_code = response.status_code
        data = response.data
        
        # Gera uma mensagem de erro descritiva
        if isinstance(data, dict):
            if 'detail' in data:
                error_msg = str(data['detail'])
                details = data
            else:
                error_msg = "Erro de validacao nos campos informados."
                details = data
        elif isinstance(data, list):
            error_msg = str(data[0]) if data else "Erro na requisicao."
            details = {"errors": data}
        else:
            error_msg = str(data)
            details = None

        custom_data = {
            "error": error_msg,
            "details": details,
            "status_code": status_code
        }
        
        response.data = custom_data
    else:
        # Erros inesperados de servidor (500)
        logger.exception("Erro interno do servidor: %s", str(exc))
        custom_data = {
            "error": "Ocorreu um erro interno no servidor.",
            "details": str(exc),
            "status_code": 500
        }
        response = Response(custom_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return response
