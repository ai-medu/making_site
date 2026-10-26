import os
from django.conf import settings
from django.core.files.storage import FileSystemStorage


class PrivateStorage(FileSystemStorage):
    """증빙 서류 보관용 비공개 저장소.

    MEDIA_ROOT 밖(PRIVATE_MEDIA_ROOT)에 두어 주소만 알아서는 열 수 없고,
    로그인·권한 확인을 거치는 뷰로만 제공한다. 위치는 설정을 그때그때 읽는다.
    """

    @property
    def base_location(self):
        return settings.PRIVATE_MEDIA_ROOT

    @property
    def location(self):
        return os.path.abspath(self.base_location)


def get_private_storage():
    return PrivateStorage()
