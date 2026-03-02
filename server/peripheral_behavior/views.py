from rest_framework import viewsets

from .models import MenuItem, TerminalAccount

from .serializers.menu import MenuPolymorphicSerializer, TerminalAccountSerializer


class MenuViewSet(viewsets.ModelViewSet):
    queryset = MenuItem.objects.all()
    serializer_class = MenuPolymorphicSerializer


class TerminalAccountViewSet(viewsets.ModelViewSet):
    queryset = TerminalAccount.objects.all()
    serializer_class = TerminalAccountSerializer
