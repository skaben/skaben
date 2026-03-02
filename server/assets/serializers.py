from assets.models import AudioFile, HackGame, ImageFile, SkabenFile, TextFile, UserInput, VideoFile
from rest_framework import serializers


class UserInputSerializer(serializers.ModelSerializer):
    """Serializer for menu item objects"""

    class Meta:
        model = UserInput
        exclude = ("uuid",)


class FileSerializer(serializers.ModelSerializer):
    file = serializers.SerializerMethodField("get_file_url")

    class Meta:
        model = SkabenFile
        abstract = True
        exclude = ("uuid", "hash")

    def get_file_url(self, obj):
        return self.context["request"].build_absolute_uri(obj.file.path)


class AudioFileSerializer(FileSerializer):
    class Meta:
        model = AudioFile
        exclude = FileSerializer.Meta.exclude


class VideoFileSerializer(FileSerializer):
    class Meta:
        model = VideoFile
        exclude = FileSerializer.Meta.exclude


class ImageFileSerializer(FileSerializer):
    class Meta:
        model = ImageFile
        exclude = FileSerializer.Meta.exclude


class TextFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = TextFile
        exclude = FileSerializer.Meta.exclude + ("ident", "content")


class HackGameSerializer(serializers.ModelSerializer):
    class Meta:
        model = HackGame
        exclude = ("id",)
