import os

from django.core.files.storage import FileSystemStorage

storage_dirs = ["audio", "video", "image", "text"]

for d in storage_dirs:
    os.makedirs(f"/media/{d}", exist_ok=True)


class OverwriteStorage(FileSystemStorage):
    def get_available_name(self, name, max_length=None):
        if self.exists(name):
            os.remove(os.path.join(self.location, name))
        return super().get_available_name(name, max_length)


audio_storage = OverwriteStorage(location="/media/audio/")
video_storage = OverwriteStorage(location="/media/video/")
image_storage = OverwriteStorage(location="/media/image/")
text_storage = OverwriteStorage(location="/media/text/")
