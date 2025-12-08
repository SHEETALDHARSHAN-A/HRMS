# app/modules/service/Upload_jd_file/base.py

from abc import ABC, abstractmethod

class BaseUploadJobPost(ABC):

    @abstractmethod
    async def job_details_file_upload(self, file):
        pass
