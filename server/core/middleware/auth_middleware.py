class AuthRequiredMiddleware(object):
    allowed = ("/auth/login", "/auth/token", "/favicon")

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # if not hasattr(request, "user") or not request.user.is_authenticated:
        #    if not request.path_info.startswith(self.allowed):
        #        return HttpResponseRedirect('/auth/login')

        return self.get_response(request)
