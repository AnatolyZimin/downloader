import hashlib
import logging
import os

from concurrent import futures
from urllib.parse import urlsplit

import requests

logger = logging.getLogger('downloader')


class Downloader:

    def __init__(
        self,
        save_path,
        session=requests.Session(),
        pool=futures.ThreadPoolExecutor(max_workers=5),
    ):
        self.save_path = save_path
        self.session = session
        self.pool = pool
        self.tasks = set()

    def download(self, url, filename=None, stream=True, **kwargs):
        filename = filename or self.make_filename(url)
        filename = os.path.join(self.save_path, filename)

        logger.info(
            'started downloading: %(url)s => %(file)s',
            {'url': url, 'file': filename},
        )

        response = self.session.get(url, stream=stream, **kwargs)

        if response.status_code != 200:
            logger.error(
                'unexpected status code %(status_code)s, '
                'URL: %(url)s',
                {'status_code': response.status_code, 'url': url},
            )
            return

        with open(filename, 'wb') as file:
            # use `chunk_size=None` to automatically set chunk size
            for chunk in response.iter_content(chunk_size=None):
                file.write(chunk)

        logger.info(
            'downloading completed: %(file)s',
            {'file': filename},
        )

    def enqueue(self, url, filename=None, stream=True, **kwargs):
        task = self.pool.submit(
            self.download,
            url,
            filename=filename,
            stream=stream,
            **kwargs
        )
        self.tasks.add(task)
        task.add_done_callback(self.tasks.remove)

    def wait(self):
        futures.wait(self.tasks)

    @staticmethod
    def make_filename(url: str) -> str:
        """
        return filename taking from `url` or name which contains `url` domain
        and md5 hash of whole `url` if filename could not be detected
        """
        url_parts = urlsplit(url)
        filename = os.path.basename(url_parts.path)
        if filename:
            return filename
        return f'{url_parts.netloc}.' + hashlib.md5(url.encode()).hexdigest()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.wait()


def main(*urls, **options):
    logging.basicConfig(
        # level=self.get_logger_level(options.get('verbosity')),
        level=logging.INFO,
        format='%(asctime)s (%(name)s) [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )

    with Downloader(save_path='.') as downloader:
        downloader.enqueue('https://avatars1.githubusercontent.com/u/3508656')


if __name__ == '__main__':
    main()
