from rest_framework import serializers
from rest_polymorphic.serializers import PolymorphicSerializer
from assets.serializers import (
    AudioFileSerializer,
    VideoFileSerializer,
    ImageFileSerializer,
    TextFileSerializer,
)
from peripheral_behavior.models import (
    MenuItem,
    MenuItemAudio,
    MenuItemVideo,
    MenuItemImage,
    MenuItemText,
    MenuItemUserInput,
    TerminalAccount,
    TerminalMenuSet,
)


class MenuItemSerializer(serializers.ModelSerializer):
    hash = serializers.SerializerMethodField()

    class Meta:
        model = MenuItem
        fields = ("timer", "label")


class MenuItemAudioSerializer(serializers.ModelSerializer):
    content = AudioFileSerializer()

    class Meta:
        model = MenuItemAudio
        fields = MenuItemSerializer.Meta.fields + ("content",)


class MenuItemVideoSerializer(serializers.ModelSerializer):
    content = VideoFileSerializer()

    class Meta:
        model = MenuItemVideo
        fields = MenuItemSerializer.Meta.fields + ("content",)


class MenuItemImageSerializer(serializers.ModelSerializer):
    content = ImageFileSerializer()

    class Meta:
        model = MenuItemImage
        fields = MenuItemSerializer.Meta.fields + ("content",)


class MenuItemTextSerializer(serializers.ModelSerializer):
    content = TextFileSerializer()

    class Meta:
        model = MenuItemText
        fields = MenuItemSerializer.Meta.fields + ("content",)


class MenuItemUserInputSerializer(serializers.ModelSerializer):
    class Meta:
        model = MenuItemUserInput
        fields = MenuItemSerializer.Meta.fields + ("input_label", "input_description")


class MenuPolymorphicSerializer(PolymorphicSerializer):
    model_serializer_mapping = {
        MenuItemAudio: MenuItemAudioSerializer,
        MenuItemVideo: MenuItemVideoSerializer,
        MenuItemImage: MenuItemImageSerializer,
        MenuItemText: MenuItemTextSerializer,
        MenuItemUserInput: MenuItemUserInputSerializer,
    }


class TerminalAccountSerializer(serializers.ModelSerializer):
    menu_items = MenuPolymorphicSerializer(many=True, read_only=True)

    def get_hash(self, obj):
        return obj.get_hash()

    class Meta:
        model = TerminalAccount
        fields = ("uuid", "menu_items", "user", "password", "header", "footer")


class TerminalMenuSetSerializer(serializers.ModelSerializer):
    account = TerminalAccountSerializer()

    class Meta:
        model = TerminalMenuSet
        fields = ("account",)
