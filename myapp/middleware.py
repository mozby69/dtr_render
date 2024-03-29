from datetime import datetime

class CurrentTimeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        request.current_time = datetime.now()

        response = self.get_response(request)

        return response
