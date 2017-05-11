#!/usr/bin/env python
import argparse
import hashlib
import logging
import os
import sys

from concurrent import futures
from typing import Set
from urllib.parse import urlsplit

import requests

logger = logging.getLogger('downloader')


class Downloader:

    def __init__(
        self,
        save_path='',
        session=requests.Session(),
        max_workers=5,
        chunk_size=10 * 1024,
    ):
        self.save_path = save_path
        self.session = session
        self.pool = futures.ThreadPoolExecutor(max_workers=max_workers)
        self.chunk_size = chunk_size
        self.tasks = set()  # type: Set[futures.Future]
        self._is_cancelled = False

    def download(self, url, filename=None, stream=True, **kwargs):
        filename = filename or self.make_filename(url)
        filename = os.path.join(self.save_path, filename)

        logger.info(
            'download started: %(url)s => %(file)s',
            {'url': url, 'file': filename},
        )

        try:
            response = self.session.get(url, stream=stream, **kwargs)
        except Exception:
            logger.exception('download error')
            return

        if response.status_code != 200:
            logger.error(
                'unexpected status code %(status_code)s, '
                'URL: %(url)s',
                {'status_code': response.status_code, 'url': url},
            )
            return

        # mimetypes module can be used to detect file extensions
        # based on value of Content-Type header

        with open(filename, 'wb') as file:
            for chunk in response.iter_content(chunk_size=self.chunk_size):

                if self._is_cancelled:
                    logger.warning('download cancelled: %(url)s', {'url': url})
                    return

                file.write(chunk)

        logger.info(
            'download completed: %(file)s',
            {'file': filename},
        )

    def enqueue(self, url, filename=None, stream=True, **kwargs):
        if self._is_cancelled:
            raise RuntimeError('Downloader was cancelled')

        task = self.pool.submit(
            self.download,
            url,
            filename=filename,
            stream=stream,
            **kwargs
        )
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)

    def wait(self):
        futures.wait(self.tasks)

    def cancel(self):
        for task in self.tasks:
            task.cancel()
        self._is_cancelled = True

    def shutdown(self, wait=True):
        self.pool.shutdown(wait=wait)

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
        try:
            self.wait()
        except:
            self.cancel()
            raise
        finally:
            self.shutdown()


def main(*urls, log_level='INFO', **options):
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )

    try:
        with Downloader(**options) as downloader:
            for url in urls:
                downloader.enqueue(url)
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    args_parser = argparse.ArgumentParser(description='files download utility')
    args_parser.add_argument('-w', '--workers', type=int, dest='max_workers',
                             default=5, help='max number of workers to use')
    args_parser.add_argument('-s', '--chunk-size', type=int, default=10 * 1024,
                             help='using size of chunks')
    args_parser.add_argument('-p', '--save-path', default='.',
                             help='path to directory where to save files')
    args_parser.add_argument('-l', '--log-level', choices=logging._nameToLevel,
                             default='INFO', help='logging level')
    args_parser.add_argument('url', nargs='+', help='URL to download')

    parsed_args = vars(args_parser.parse_args(sys.argv[1:]))
    urls = parsed_args.pop('url')

    main(*urls, **parsed_args)
